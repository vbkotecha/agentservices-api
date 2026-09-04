"""
Hyperliquid execution door — policy-checked forwarding of agent-signed L1 actions.

AgentServices does NOT hold venue API keys or user private keys. Agents sign orders
locally with an HL-approved agent wallet (approveAgent on the main wallet) and send
the signed payload here for policy enforcement before forwarding to Hyperliquid.

Execution is free at call time (no x402). Optional builder fees are omitted so routing
through AgentServices is not more expensive than HL direct.
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

MarketType = Literal["spot", "perp", "future"]
VALID_MARKET_TYPES: frozenset[str] = frozenset({"spot", "perp", "future"})
# Hyperliquid currently implements perp + spot; dated futures are not routed here yet.
HL_SUPPORTED_MARKET_TYPES: frozenset[str] = frozenset({"perp", "spot"})

HL_API_URL = os.environ.get("HYPERLIQUID_API_URL", "https://api.hyperliquid.xyz").rstrip("/")
HL_EXCHANGE_URL = f"{HL_API_URL}/exchange"
HL_INFO_URL = f"{HL_API_URL}/info"

# Perp asset indices on HL mainnet (fallback when meta fetch fails)
_DEFAULT_ASSET_INDEX: dict[str, int] = {"BTC": 0, "ETH": 1}
_INDEX_TO_COIN: dict[int, str] = {v: k for k, v in _DEFAULT_ASSET_INDEX.items()}
_meta_cache: dict[str, Any] = {"fetched_at": 0, "index_to_coin": dict(_INDEX_TO_COIN)}

_POLICY_DIR: Path | None = None
_paper_orders: dict[str, list[dict]] = {}
_paper_counter = 0


def _is_serverless() -> bool:
    return any(os.environ.get(name) for name in ("VERCEL", "VERCEL_ENV", "AWS_LAMBDA_FUNCTION_NAME"))


def _policy_dir() -> Path:
    global _POLICY_DIR
    if _POLICY_DIR is not None:
        return _POLICY_DIR
    override = os.environ.get("AGENTSERVICES_HL_POLICY_DIR")
    candidates = [Path(override)] if override else []
    if _is_serverless():
        candidates.append(Path("/tmp/agentservices-hl-policies"))
    else:
        candidates.append(Path("/tmp/agentservices-hl-policies"))
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            _POLICY_DIR = candidate
            return _POLICY_DIR
        except OSError:
            continue
    raise OSError("No writable directory for HL policies")


def _policy_path(principal: str) -> Path:
    safe = hashlib.sha256(principal.lower().encode()).hexdigest()[:16]
    return _policy_dir() / f"{safe}.json"


class HLExecutionPolicy(BaseModel):
    """Leash a principal installs for agent trading."""

    principal: str = Field(description="Main HL wallet address (0x…)")
    max_notional_usd: float = Field(default=50_000.0, description="Max USD notional per order")
    allowed_coins: list[str] = Field(default_factory=lambda: ["BTC", "ETH"])
    enabled: bool = Field(default=True, description="Master enable for this principal")
    kill_switch: bool = Field(default=False, description="Emergency halt — reject all orders")


class SignedHLPayload(BaseModel):
    """Agent-signed Hyperliquid exchange payload (L1 action)."""

    action: dict = Field(description="HL action object (type order, cancel, etc.)")
    nonce: int = Field(description="HL nonce (ms timestamp recommended)")
    signature: dict = Field(description="EIP-712 signature {r,s,v}")
    vaultAddress: str | None = Field(default=None, description="Vault/subaccount if applicable")
    expiresAfter: int | None = Field(default=None)


class OrderCheckFields(BaseModel):
    """Explicit order fields for policy when action parsing is insufficient."""

    coin: str | None = None
    side: str | None = Field(default=None, description="buy or sell")
    size: float | None = None
    price: float | None = None


def validate_market_type(market_type: str, venue: str = "hyperliquid") -> str:
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
    if venue == "hyperliquid" and normalized not in HL_SUPPORTED_MARKET_TYPES:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "market_type_not_supported",
                "market_type": normalized,
                "venue": venue,
                "supported": sorted(HL_SUPPORTED_MARKET_TYPES),
            },
        )
    return normalized


class HLForwardRequest(BaseModel):
    principal: str = Field(description="Main wallet the agent trades on behalf of")
    market_type: MarketType = Field(default="perp", description="Market type: spot, perp, or future")
    signed: SignedHLPayload
    check: OrderCheckFields | None = Field(
        default=None,
        description="Optional explicit fields for policy; otherwise parsed from action",
    )

    @field_validator("market_type", mode="before")
    @classmethod
    def _normalize_market_type(cls, v: str) -> str:
        if isinstance(v, str):
            return v.lower().strip()
        return v


class HLPolicyEvalRequest(BaseModel):
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


class HLPaperOrderRequest(BaseModel):
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


def _fetch_meta() -> dict[int, str]:
    now = time.time()
    if now - _meta_cache["fetched_at"] < 300 and _meta_cache["index_to_coin"]:
        return _meta_cache["index_to_coin"]
    try:
        resp = requests.post(HL_INFO_URL, json={"type": "meta"}, timeout=10)
        resp.raise_for_status()
        universe = resp.json().get("universe") or []
        mapping: dict[int, str] = {}
        for idx, asset in enumerate(universe):
            name = asset.get("name") if isinstance(asset, dict) else str(asset)
            if name:
                mapping[idx] = name.upper()
        if mapping:
            _meta_cache["index_to_coin"] = mapping
            _meta_cache["fetched_at"] = now
            return mapping
    except requests.RequestException:
        pass
    return _meta_cache["index_to_coin"] or dict(_INDEX_TO_COIN)


def coin_for_asset_index(asset_index: int) -> str | None:
    return _fetch_meta().get(asset_index)


def asset_index_for_coin(coin: str) -> int | None:
    coin = coin.upper()
    for idx, name in _fetch_meta().items():
        if name == coin:
            return idx
    return _DEFAULT_ASSET_INDEX.get(coin)


def get_policy(principal: str) -> HLExecutionPolicy:
    path = _policy_path(principal)
    if not path.exists():
        return HLExecutionPolicy(principal=principal)
    try:
        data = json.loads(path.read_text())
        return HLExecutionPolicy(**data)
    except (json.JSONDecodeError, ValueError):
        return HLExecutionPolicy(principal=principal)


def set_policy(policy: HLExecutionPolicy) -> HLExecutionPolicy:
    policy.allowed_coins = [c.upper() for c in policy.allowed_coins]
    path = _policy_path(policy.principal)
    path.write_text(policy.model_dump_json(indent=2))
    return policy


def _parse_order_legs(action: dict) -> list[dict]:
    if action.get("type") != "order":
        return []
    legs = []
    for order in action.get("orders") or []:
        asset_idx = order.get("a")
        coin = coin_for_asset_index(asset_idx) if asset_idx is not None else None
        is_buy = order.get("b")
        size = float(order.get("s", 0) or 0)
        price = float(order.get("p", 0) or 0)
        side = "buy" if is_buy else "sell"
        legs.append(
            {
                "coin": coin,
                "side": side,
                "size": size,
                "price": price,
                "notional_usd": size * price,
                "asset_index": asset_idx,
            }
        )
    return legs


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


def _strip_builder_fee(action: dict) -> dict:
    """Remove builder tag so execution is not more expensive than HL direct."""
    cleaned = deepcopy(action)
    cleaned.pop("builder", None)
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
            "venue": "hyperliquid",
            "coin": coin.upper(),
            "notional_usd": size * price,
        }
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {"error": str(exc.detail)}
        return {"pass": False, "principal": principal, "market_type": normalized_market, "reason": detail}


def _build_forward_body(signed: SignedHLPayload) -> dict:
    action = _strip_builder_fee(signed.action)
    body: dict[str, Any] = {
        "action": action,
        "nonce": signed.nonce,
        "signature": signed.signature,
    }
    if signed.vaultAddress:
        body["vaultAddress"] = signed.vaultAddress
    if signed.expiresAfter is not None:
        body["expiresAfter"] = signed.expiresAfter
    return body


def forward_signed_action(req: HLForwardRequest) -> dict:
    """Policy-check then forward agent-signed payload to Hyperliquid."""
    market_type = validate_market_type(req.market_type)
    action = req.signed.action
    action_type = action.get("type")
    if action_type == "order":
        legs = _parse_order_legs(action)
        legs = _merge_check_fields(legs, req.check)
        validate_order_policy(req.principal, legs)
    elif action_type in ("cancel", "cancelByCloid"):
        policy = get_policy(req.principal)
        if policy.kill_switch or not policy.enabled:
            raise HTTPException(
                status_code=403,
                detail={"error": "execution_disabled", "principal": req.principal},
            )
    else:
        raise HTTPException(
            status_code=400,
            detail={"error": "unsupported_action_type", "type": action_type, "supported": ["order", "cancel", "cancelByCloid"]},
        )

    body = _build_forward_body(req.signed)
    try:
        resp = requests.post(HL_EXCHANGE_URL, json=body, timeout=15)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail={"error": "hyperliquid_unreachable", "message": str(exc)}) from exc

    try:
        hl_result = resp.json()
    except ValueError:
        raise HTTPException(status_code=502, detail={"error": "invalid_hyperliquid_response", "status": resp.status_code})

    receipt = _build_receipt(req, body, hl_result, legs if action_type == "order" else [], market_type)
    return {"receipt": receipt, "hyperliquid": hl_result, "market_type": market_type}


def _build_receipt(
    req: HLForwardRequest, body: dict, hl_result: dict, legs: list[dict], market_type: str = "perp"
) -> dict:
    ts = int(time.time() * 1000)
    receipt: dict[str, Any] = {
        "principal": req.principal,
        "market_type": market_type,
        "venue": "hyperliquid",
        "action_type": body["action"].get("type"),
        "timestamp_ms": ts,
        "forwarded_to": HL_EXCHANGE_URL,
        "builder_fee": None,
        "note": "Execution evidence only — not a billed SKU. Same fill as HL direct.",
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
    oid = _extract_order_id(hl_result)
    if oid is not None:
        receipt["order_id"] = oid
    return receipt


def _extract_order_id(hl_result: dict) -> int | str | None:
    try:
        statuses = hl_result.get("response", {}).get("data", {}).get("statuses") or []
        if not statuses:
            return None
        status = statuses[0]
        if "resting" in status:
            return status["resting"].get("oid")
        if "filled" in status:
            return status["filled"].get("oid")
    except (AttributeError, TypeError, KeyError):
        return None
    return None


def get_order_status(user: str, oid: int | str) -> dict:
    """Read-only status via HL info API (no signing required)."""
    try:
        resp = requests.post(
            HL_INFO_URL,
            json={"type": "orderStatus", "user": user, "oid": int(oid)},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail={"error": "hyperliquid_info_failed", "message": str(exc)}) from exc


def place_paper_order(req: HLPaperOrderRequest) -> dict:
    """Simulated order — same shape as live, no HL call."""
    global _paper_counter
    market_type = validate_market_type(req.market_type)
    policy = get_policy(req.principal) if req.principal != "paper-agent" else HLExecutionPolicy(principal=req.principal)
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
        "venue": "hyperliquid",
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
            "venue": "hyperliquid",
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
        "venue": "hyperliquid",
        "base_path": "/v1/trade/hyperliquid",
        "market_types": {
            "accepted": sorted(VALID_MARKET_TYPES),
            "supported_now": sorted(HL_SUPPORTED_MARKET_TYPES),
        },
        "model": "agent_sign_only",
        "venue_api_keys": "never_collected",
        "human_bootstrap": [
            "1. Main wallet approves an agent via Hyperliquid approveAgent (user-signed, on-chain).",
            "2. Agent wallet signs L1 actions (order/cancel) locally — private key stays with the agent.",
            "3. Agent sends signed payload + principal address to AgentServices for policy check and forward.",
        ],
        "builder_fee": "omitted (0) — execution through AgentServices is not more expensive than HL direct",
        "x402": "not_used_on_execution_path",
        "approve_builder_fee": "not_supported_here — main-wallet action only; agents cannot enable builder fees via this API",
        "docs": "https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/exchange-endpoint",
    }
