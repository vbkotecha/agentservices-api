"""
Pacifica execution door — policy-checked forwarding of agent-signed orders.

AgentServices does NOT hold venue API keys or user private keys. Agents sign orders
locally with a Pacifica Agent Wallet (bind_agent_wallet on the main account) and send
the signed payload here for policy enforcement before forwarding to Pacifica.

Execution is free at call time (no x402). Builder codes are stripped so routing
through AgentServices is not more expensive than Pacifica direct.
"""
from __future__ import annotations

import json
import os
import time
import hashlib
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal

import requests
from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator

from hyperliquid_data import VALID_MARKET_TYPES, OrderCheckFields

MarketType = Literal["spot", "perp", "future"]
# Pacifica implements perp + spot via unified order endpoints; dated futures not routed here yet.
PAC_SUPPORTED_MARKET_TYPES: frozenset[str] = frozenset({"perp", "spot"})

PAC_API_URL = os.environ.get("PACIFICA_API_URL", "https://api.pacifica.fi").rstrip("/")

OPERATION_ENDPOINTS: dict[str, str] = {
    "create_order": "/api/v1/orders/create",
    "create_market_order": "/api/v1/orders/create_market",
    "cancel_order": "/api/v1/orders/cancel",
}

ORDER_OPERATIONS: frozenset[str] = frozenset({"create_order", "create_market_order"})
CANCEL_OPERATIONS: frozenset[str] = frozenset({"cancel_order"})

_prices_cache: dict[str, Any] = {"fetched_at": 0, "by_symbol": {}}

_POLICY_DIR: Path | None = None
_paper_orders: dict[str, list[dict]] = {}
_paper_counter = 0


def _is_serverless() -> bool:
    return any(os.environ.get(name) for name in ("VERCEL", "VERCEL_ENV", "AWS_LAMBDA_FUNCTION_NAME"))


def _policy_dir() -> Path:
    global _POLICY_DIR
    if _POLICY_DIR is not None:
        return _POLICY_DIR
    override = os.environ.get("AGENTSERVICES_PACIFICA_POLICY_DIR")
    candidates = [Path(override)] if override else []
    candidates.append(Path("/tmp/agentservices-pacifica-policies"))
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            _POLICY_DIR = candidate
            return _POLICY_DIR
        except OSError:
            continue
    raise OSError("No writable directory for Pacifica policies")


def _policy_path(principal: str) -> Path:
    safe = hashlib.sha256(principal.encode()).hexdigest()[:16]
    return _policy_dir() / f"{safe}.json"


class PacificaExecutionPolicy(BaseModel):
    """Leash a principal installs for agent trading."""

    principal: str = Field(description="Main Pacifica account address")
    max_notional_usd: float = Field(default=50_000.0, description="Max USD notional per order")
    allowed_coins: list[str] = Field(default_factory=lambda: ["BTC", "ETH"])
    enabled: bool = Field(default=True, description="Master enable for this principal")
    kill_switch: bool = Field(default=False, description="Emergency halt — reject all orders")


class SignedPacificaPayload(BaseModel):
    """Agent-signed Pacifica request ready to forward."""

    operation: Literal["create_order", "create_market_order", "cancel_order"] = Field(
        description="Pacifica operation type (maps to REST endpoint)"
    )
    request: dict = Field(
        description="Complete signed Pacifica request body (account, signature, timestamp, …)"
    )


def validate_market_type(market_type: str, venue: str = "pacifica") -> str:
    """Validate market_type enum and venue support. Returns normalized market_type."""
    normalized = market_type.lower().strip()
    if normalized not in VALID_MARKET_TYPES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_market_type",
                "market_type": market_type,
                "allowed": sorted(VALID_MARKET_TYPES),
            },
        )
    if venue == "pacifica" and normalized not in PAC_SUPPORTED_MARKET_TYPES:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "market_type_not_supported",
                "market_type": normalized,
                "venue": venue,
                "supported": sorted(PAC_SUPPORTED_MARKET_TYPES),
            },
        )
    return normalized


class PacificaForwardRequest(BaseModel):
    principal: str = Field(description="Main account the agent trades on behalf of")
    market_type: MarketType = Field(default="perp", description="Market type: spot, perp, or future")
    signed: SignedPacificaPayload
    check: OrderCheckFields | None = Field(
        default=None,
        description="Optional explicit fields for policy; otherwise parsed from signed request",
    )

    @field_validator("market_type", mode="before")
    @classmethod
    def _normalize_market_type(cls, v: str) -> str:
        if isinstance(v, str):
            return v.lower().strip()
        return v


class PacificaPolicyEvalRequest(BaseModel):
    principal: str
    market_type: MarketType = Field(default="perp", description="Market type: spot, perp, or future")
    coin: str
    side: str
    size: float
    price: float

    @field_validator("market_type", mode="before")
    @classmethod
    def _normalize_market_type(cls, v: str) -> str:
        if isinstance(v, str):
            return v.lower().strip()
        return v


class PacificaPaperOrderRequest(BaseModel):
    principal: str = "paper-agent"
    market_type: MarketType = Field(default="perp", description="Market type: spot, perp, or future")
    coin: str = "BTC"
    side: str = "buy"
    size: float = 0.01
    price: float = 50_000.0
    order_type: str = "limit"

    @field_validator("market_type", mode="before")
    @classmethod
    def _normalize_market_type(cls, v: str) -> str:
        if isinstance(v, str):
            return v.lower().strip()
        return v


def get_policy(principal: str) -> PacificaExecutionPolicy:
    path = _policy_path(principal)
    if not path.exists():
        return PacificaExecutionPolicy(principal=principal)
    try:
        data = json.loads(path.read_text())
        return PacificaExecutionPolicy(**data)
    except (json.JSONDecodeError, ValueError):
        return PacificaExecutionPolicy(principal=principal)


def set_policy(policy: PacificaExecutionPolicy) -> PacificaExecutionPolicy:
    policy.allowed_coins = [c.upper() for c in policy.allowed_coins]
    path = _policy_path(policy.principal)
    path.write_text(policy.model_dump_json(indent=2))
    return policy


def _fetch_mark_prices() -> dict[str, float]:
    now = time.time()
    if now - _prices_cache["fetched_at"] < 60 and _prices_cache["by_symbol"]:
        return _prices_cache["by_symbol"]
    try:
        resp = requests.get(f"{PAC_API_URL}/api/v1/info/prices", timeout=10)
        resp.raise_for_status()
        rows = resp.json().get("data") or []
        mapping: dict[str, float] = {}
        for row in rows:
            symbol = (row.get("symbol") or "").upper()
            mark = row.get("mark")
            if symbol and mark is not None:
                mapping[symbol] = float(mark)
        if mapping:
            _prices_cache["by_symbol"] = mapping
            _prices_cache["fetched_at"] = now
            return mapping
    except (requests.RequestException, ValueError, TypeError):
        pass
    return _prices_cache["by_symbol"]


def _side_from_pacifica(side: str) -> str:
    s = side.lower().strip()
    if s == "bid":
        return "buy"
    if s == "ask":
        return "sell"
    return s


def _parse_order_leg(body: dict, operation: str) -> list[dict]:
    if operation not in ORDER_OPERATIONS:
        return []
    symbol = (body.get("symbol") or "").upper()
    side = _side_from_pacifica(body.get("side") or "")
    size = float(body.get("amount", 0) or 0)
    price_raw = body.get("price")
    price = float(price_raw) if price_raw is not None else 0.0
    if price <= 0 and operation == "create_market_order":
        price = _fetch_mark_prices().get(symbol, 0.0)
    notional = size * price if price > 0 else 0.0
    return [
        {
            "coin": symbol,
            "side": side,
            "size": size,
            "price": price,
            "notional_usd": notional,
        }
    ]


def _merge_check_fields(legs: list[dict], check: OrderCheckFields | None) -> list[dict]:
    if not check or not legs:
        return legs
    merged = []
    for leg in legs:
        item = dict(leg)
        if check.coin:
            item["coin"] = check.coin.upper()
        if check.side:
            item["side"] = check.side.lower()
        if check.size is not None:
            item["size"] = check.size
        if check.price is not None:
            item["price"] = check.price
        item["notional_usd"] = item.get("size", 0) * item.get("price", 0)
        merged.append(item)
    return merged


def _strip_builder_code(body: dict) -> dict:
    """Remove builder code so execution is not more expensive than Pacifica direct."""
    cleaned = deepcopy(body)
    cleaned.pop("builder_code", None)
    return cleaned


def validate_order_policy(principal: str, legs: list[dict]) -> None:
    policy = get_policy(principal)
    if policy.kill_switch:
        raise HTTPException(status_code=403, detail={"error": "kill_switch_active", "principal": principal})
    if not policy.enabled:
        raise HTTPException(status_code=403, detail={"error": "execution_disabled", "principal": principal})
    if not legs:
        raise HTTPException(status_code=400, detail={"error": "no_orders_in_action"})
    allowed = {c.upper() for c in policy.allowed_coins}
    for leg in legs:
        coin = (leg.get("coin") or "").upper()
        if not coin:
            raise HTTPException(status_code=400, detail={"error": "unknown_asset", "leg": leg})
        if coin not in allowed:
            raise HTTPException(
                status_code=403,
                detail={"error": "coin_not_allowlisted", "coin": coin, "allowed": sorted(allowed)},
            )
        notional = leg.get("notional_usd") or 0
        if notional <= 0:
            raise HTTPException(
                status_code=400,
                detail={"error": "cannot_compute_notional", "coin": coin, "hint": "provide check.price for market orders"},
            )
        if notional > policy.max_notional_usd:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "max_notional_exceeded",
                    "notional_usd": notional,
                    "max_notional_usd": policy.max_notional_usd,
                    "coin": coin,
                },
            )


def eval_order_against_policy(
    principal: str,
    coin: str,
    side: str,
    size: float,
    price: float,
    market_type: str = "perp",
) -> dict:
    """Training gym: pass/fail a candidate order against a principal's policy."""
    normalized_market = validate_market_type(market_type)
    legs = [{"coin": coin.upper(), "side": side.lower(), "size": size, "price": price, "notional_usd": size * price}]
    try:
        validate_order_policy(principal, legs)
        return {
            "pass": True,
            "principal": principal,
            "market_type": normalized_market,
            "venue": "pacifica",
            "coin": coin.upper(),
            "notional_usd": size * price,
        }
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {"error": str(exc.detail)}
        return {"pass": False, "principal": principal, "market_type": normalized_market, "reason": detail}


def forward_signed_action(req: PacificaForwardRequest) -> dict:
    """Policy-check then forward agent-signed payload to Pacifica."""
    market_type = validate_market_type(req.market_type)
    operation = req.signed.operation
    body = req.signed.request

    if operation not in OPERATION_ENDPOINTS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unsupported_operation",
                "operation": operation,
                "supported": sorted(OPERATION_ENDPOINTS),
            },
        )

    if operation in ORDER_OPERATIONS:
        legs = _parse_order_leg(body, operation)
        legs = _merge_check_fields(legs, req.check)
        validate_order_policy(req.principal, legs)
    elif operation in CANCEL_OPERATIONS:
        policy = get_policy(req.principal)
        if policy.kill_switch or not policy.enabled:
            raise HTTPException(
                status_code=403,
                detail={"error": "execution_disabled", "principal": req.principal},
            )
        legs = []
    else:
        legs = []

    forward_body = _strip_builder_code(body)
    endpoint = OPERATION_ENDPOINTS[operation]
    url = f"{PAC_API_URL}{endpoint}"
    try:
        resp = requests.post(url, json=forward_body, timeout=15)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail={"error": "pacifica_unreachable", "message": str(exc)}) from exc

    try:
        pac_result = resp.json()
    except ValueError:
        raise HTTPException(
            status_code=502,
            detail={"error": "invalid_pacifica_response", "status": resp.status_code},
        )

    receipt = _build_receipt(req, operation, url, pac_result, legs, market_type)
    return {"receipt": receipt, "pacifica": pac_result, "market_type": market_type}


def _build_receipt(
    req: PacificaForwardRequest,
    operation: str,
    url: str,
    pac_result: dict,
    legs: list[dict],
    market_type: str = "perp",
) -> dict:
    ts = int(time.time() * 1000)
    receipt: dict[str, Any] = {
        "principal": req.principal,
        "market_type": market_type,
        "venue": "pacifica",
        "operation": operation,
        "timestamp_ms": ts,
        "forwarded_to": url,
        "builder_fee": None,
        "note": "Execution evidence only — not a billed SKU. Same fill as Pacifica direct.",
    }
    if legs:
        receipt["orders"] = [
            {
                "coin": leg.get("coin"),
                "side": leg.get("side"),
                "size": leg.get("size"),
                "price": leg.get("price"),
                "notional_usd": leg.get("notional_usd"),
            }
            for leg in legs
        ]
    oid = _extract_order_id(pac_result)
    if oid is not None:
        receipt["order_id"] = oid
    return receipt


def _extract_order_id(pac_result: dict) -> int | str | None:
    oid = pac_result.get("order_id")
    if oid is not None:
        return oid
    data = pac_result.get("data")
    if isinstance(data, dict):
        return data.get("order_id")
    return None


def get_order_status(user: str, oid: int | str) -> dict:
    """Read-only status via Pacifica orders API (no signing required)."""
    try:
        resp = requests.get(
            f"{PAC_API_URL}/api/v1/orders/history_by_id",
            params={"order_id": int(oid)},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail={"error": "pacifica_info_failed", "message": str(exc)}) from exc


def place_paper_order(req: PacificaPaperOrderRequest) -> dict:
    """Simulated order — same shape as live, no Pacifica call."""
    global _paper_counter
    market_type = validate_market_type(req.market_type)
    if req.principal != "paper-agent":
        legs = [
            {
                "coin": req.coin.upper(),
                "side": req.side.lower(),
                "size": req.size,
                "price": req.price,
                "notional_usd": req.size * req.price,
            }
        ]
        validate_order_policy(req.principal, legs)

    _paper_counter += 1
    oid = f"paper-{_paper_counter}"
    ts = int(time.time() * 1000)
    order = {
        "order_id": oid,
        "principal": req.principal,
        "market_type": market_type,
        "venue": "pacifica",
        "coin": req.coin.upper(),
        "side": req.side.lower(),
        "size": req.size,
        "price": req.price,
        "order_type": req.order_type,
        "status": "resting",
        "timestamp_ms": ts,
        "simulated": True,
    }
    _paper_orders.setdefault(req.principal, []).append(order)
    return {
        "receipt": {
            "order_id": oid,
            "market_type": market_type,
            "venue": "pacifica",
            "coin": order["coin"],
            "side": order["side"],
            "size": order["size"],
            "price": order["price"],
            "timestamp_ms": ts,
            "simulated": True,
        },
        "paper": order,
    }


def get_paper_orders(principal: str) -> list[dict]:
    return list(_paper_orders.get(principal, []))


def bootstrap_doc() -> dict:
    return {
        "venue": "pacifica",
        "base_path": "/v1/trade/pacifica",
        "market_types": {
            "accepted": sorted(VALID_MARKET_TYPES),
            "supported_now": sorted(PAC_SUPPORTED_MARKET_TYPES),
        },
        "model": "agent_sign_only",
        "venue_api_keys": "never_collected",
        "human_bootstrap": [
            "1. Generate an Agent Wallet keypair (Ed25519) — Pacifica frontend or Python SDK.",
            "2. Main account signs bind_agent_wallet via POST /api/v1/agent/bind (user-signed, one-time).",
            "3. Agent signs create_order / create_market_order / cancel_order locally (Ed25519, Base58).",
            "4. Agent sends signed request + principal to AgentServices for policy check and forward.",
        ],
        "signing": {
            "algorithm": "Ed25519",
            "encoding": "Base58",
            "agent_field": "agent_wallet",
            "account_field": "account",
            "docs": "https://docs.pacifica.fi/api-documentation/api/signing",
        },
        "operations": {
            "create_order": "/api/v1/orders/create",
            "create_market_order": "/api/v1/orders/create_market",
            "cancel_order": "/api/v1/orders/cancel",
            "bind_agent_wallet": "/api/v1/agent/bind",
        },
        "paper": "/v1/trade/pacifica/paper/order",
        "policy": "/v1/trade/pacifica/policy",
        "builder_fee": "omitted (0) — execution through AgentServices is not more expensive than Pacifica direct",
        "x402": "not_used_on_execution_path",
        "docs": "https://docs.pacifica.fi/api-documentation/api/signing/api-agent-keys",
    }
