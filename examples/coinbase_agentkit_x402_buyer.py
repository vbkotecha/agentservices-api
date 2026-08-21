#!/usr/bin/env python3
"""Run the Coinbase AgentKit x402 buyer path against AgentServices.

The default challenge mode makes no payment. The pay mode requires both PRIVATE_KEY
and the literal --confirm-payment flag, and caps the request at $0.10 USDC.

Examples:
    python3 examples/coinbase_agentkit_x402_buyer.py --challenge
    PRIVATE_KEY=0x... python3 examples/coinbase_agentkit_x402_buyer.py \
        --pay --confirm-payment --evidence-dir ./agentservices-evidence
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import sys
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path
from typing import Any

API_BASE_URL = "https://api.agentservices.to"
DEFAULT_PATH = "/v1/token-risk/BTC"
MAX_PAYMENT_USDC = Decimal("0.10")
USDC_DECIMALS = 6


def decode_payment_required(value: str) -> dict[str, Any]:
    """Decode an x402 v2 payment-required header."""
    try:
        padding = "=" * (-len(value) % 4)
        return json.loads(base64.b64decode(value + padding).decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid payment-required header") from exc


def get_header(headers: Any, name: str) -> str | None:
    """Read a response header case-insensitively."""
    return next((value for key, value in headers.items() if key.lower() == name.lower()), None)


def amount_atomic(challenge: dict[str, Any]) -> int:
    """Return the first accepted payment amount in atomic USDC units."""
    accepts = challenge.get("accepts") or []
    if not accepts:
        raise ValueError("payment challenge has no accepted payment options")
    raw = accepts[0].get("amount") or accepts[0].get("maxAmountRequired")
    if raw is None:
        raise ValueError("payment challenge has no amount")
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("payment challenge amount is not an integer") from exc


def format_usdc(amount: int) -> str:
    """Format atomic USDC units for human-readable output."""
    return f"{Decimal(amount) / (Decimal(10) ** USDC_DECIMALS):.6f} USDC"


def fetch_challenge(url: str) -> tuple[str, dict[str, Any]]:
    """Request a paid URL and return its raw and decoded x402 challenge."""
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            raise RuntimeError(f"expected HTTP 402 from {url}, got HTTP {response.status}")
    except urllib.error.HTTPError as error:
        if error.code != 402:
            raise RuntimeError(f"expected HTTP 402 from {url}, got HTTP {error.code}") from error
        encoded = get_header(error.headers, "payment-required")
        if not encoded:
            raise RuntimeError("HTTP 402 response did not include payment-required")
        return encoded, decode_payment_required(encoded)


def write_json(path: Path, value: Any) -> None:
    """Write a JSON artifact without credentials."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_challenge(evidence_dir: Path, encoded: str, challenge: dict[str, Any]) -> None:
    """Retain the exact challenge header and decoded buyer terms."""
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "payment-required.txt").write_text(encoded + "\n", encoding="utf-8")
    write_json(evidence_dir / "payment-required.json", challenge)


def run_agentkit_payment(url: str) -> dict[str, Any]:
    """Use Coinbase AgentKit's x402 provider to pay and retry the request."""
    private_key = os.getenv("PRIVATE_KEY", "")
    if not private_key:
        raise RuntimeError("PRIVATE_KEY is required for --pay and is never written to evidence")

    try:
        from coinbase_agentkit.action_providers.x402 import X402Config, x402_action_provider
        from coinbase_agentkit.wallet_providers import (
            EthAccountWalletProvider,
            EthAccountWalletProviderConfig,
        )
        from eth_account import Account
    except ImportError as exc:
        raise RuntimeError(
            "install Coinbase AgentKit first: pip install coinbase-agentkit"
        ) from exc

    account = Account.from_key(private_key)
    wallet = EthAccountWalletProvider(
        EthAccountWalletProviderConfig(
            account=account,
            chain_id="8453",
            rpc_url=os.getenv("AGENTKIT_RPC_URL") or None,
        )
    )
    provider = x402_action_provider(
        X402Config(
            registered_services=[API_BASE_URL],
            max_payment_usdc=float(MAX_PAYMENT_USDC),
        )
    )
    result = provider.make_http_request_with_x402(
        wallet,
        {"url": url, "method": "GET"},
    )
    if not isinstance(result, str):
        raise RuntimeError("AgentKit returned an unexpected response type")
    return json.loads(result)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--challenge", action="store_true", help="inspect the live 402 only")
    mode.add_argument("--pay", action="store_true", help="pay and retry the live request")
    parser.add_argument("--url", default=API_BASE_URL + DEFAULT_PATH)
    parser.add_argument("--evidence-dir", type=Path, default=Path("agentservices-evidence"))
    parser.add_argument(
        "--confirm-payment",
        action="store_true",
        help="explicitly authorize the capped payment; required with --pay",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        encoded, challenge = fetch_challenge(args.url)
        amount = amount_atomic(challenge)
        write_challenge(args.evidence_dir, encoded, challenge)
        print(f"CHALLENGE: HTTP 402 retained at {args.evidence_dir}")
        print(f"AMOUNT: {format_usdc(amount)}")

        max_atomic = int(MAX_PAYMENT_USDC * (Decimal(10) ** USDC_DECIMALS))
        if amount > max_atomic:
            raise RuntimeError(
                f"challenge amount {format_usdc(amount)} exceeds the $0.10 safety cap; no payment attempted"
            )
        if args.challenge:
            print("NO PAYMENT: challenge mode stops before signing")
            return 0
        if not args.confirm_payment:
            raise RuntimeError("--pay requires --confirm-payment; no payment attempted")

        result = run_agentkit_payment(args.url)
        write_json(args.evidence_dir / "paid-result.json", result)
        if result.get("status") != "success" and result.get("success") is not True:
            raise RuntimeError("AgentKit did not return a successful paid result")
        details = result.get("details") or {}
        proof = details.get("paymentProof") or result.get("paymentProof")
        if proof:
            write_json(args.evidence_dir / "payment-proof.json", proof)
        print(f"PAID RESULT: HTTP 200 retained at {args.evidence_dir / 'paid-result.json'}")
        return 0
    except (RuntimeError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"BUYER PATH FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
