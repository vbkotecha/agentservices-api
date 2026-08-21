#!/usr/bin/env python3
"""Verify AgentServices' buyer discovery and x402 payment challenge without spending.

Usage:
    python3 examples/token_risk_buyer_proof.py BTC

The script proves a real buyer path:
  1. Retrieve a free market-price response.
  2. Request a paid token-risk outcome.
  3. Decode and display the x402 payment requirements returned as HTTP 402.

It does not sign, submit, or settle any payment.
"""

from __future__ import annotations

import base64
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal
from typing import Any

API_BASE_URL = "https://api.agentservices.to"
USDC_DECIMALS = 6


def request(url: str) -> tuple[int, dict[str, str], str]:
    """Return HTTP response details, preserving expected non-2xx responses."""
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            return response.status, dict(response.headers.items()), response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers.items()), error.read().decode("utf-8", errors="replace")


def header_value(headers: dict[str, str], name: str) -> str | None:
    normalized_name = name.lower()
    return next((value for key, value in headers.items() if key.lower() == normalized_name), None)


def decode_payment_required(headers: dict[str, str]) -> dict[str, Any]:
    """Decode the x402 v2 payment-required response header."""
    encoded = header_value(headers, "payment-required")
    if not encoded:
        raise ValueError("paid response did not include the payment-required header")
    padding = "=" * (-len(encoded) % 4)
    return json.loads(base64.b64decode(encoded + padding).decode("utf-8"))


def first_requirement(challenge: dict[str, Any]) -> dict[str, Any]:
    requirements = challenge.get("accepts") or challenge.get("paymentRequirements") or []
    if not requirements:
        raise ValueError("payment-required header contains no accepted payment requirement")
    return requirements[0]


def format_usdc(amount: Any) -> str:
    return f"{Decimal(str(amount)) / (Decimal(10) ** USDC_DECIMALS):.6f} USDC"


def main() -> int:
    symbol = (sys.argv[1] if len(sys.argv) > 1 else "BTC").upper()

    price_url = f"{API_BASE_URL}/v1/prices?symbols={urllib.parse.quote(symbol)}"
    price_status, _, price_body = request(price_url)
    if price_status != 200:
        print(f"Free price check failed: HTTP {price_status}\n{price_body}", file=sys.stderr)
        return 1

    print(f"FREE CHECK: {price_url} → HTTP 200")
    print(json.dumps(json.loads(price_body), indent=2, sort_keys=True))

    paid_url = f"{API_BASE_URL}/v1/token-risk/{urllib.parse.quote(symbol)}"
    paid_status, paid_headers, paid_body = request(paid_url)
    if paid_status != 402:
        print(f"Expected an x402 HTTP 402 from {paid_url}; got HTTP {paid_status}.", file=sys.stderr)
        print(paid_body, file=sys.stderr)
        return 1

    challenge = decode_payment_required(paid_headers)
    requirement = first_requirement(challenge)
    amount = requirement.get("maxAmountRequired") or requirement.get("amount")
    if amount is None:
        raise ValueError("payment requirement did not declare an amount")

    resource = challenge.get("resource") or {}
    extra = resource.get("extra") or {}
    print("\nPAID OUTCOME: token-risk report → HTTP 402 x402 challenge verified")
    print(f"service: {extra.get('serviceName', 'AgentServices')}")
    print(f"resource: {resource.get('url', paid_url)}")
    print(f"scheme: {requirement.get('scheme')}")
    print(f"network: {requirement.get('network')}")
    print(f"asset: {requirement.get('asset')}")
    print(f"amount: {amount} atomic units ({format_usdc(amount)})")
    print(f"recipient: {requirement.get('payTo')}")
    print("next step: pay the declared USDC amount with an x402-compatible Base wallet, then retry with payment proof.")
    print("This proof validates public discovery and payment requirements only; no payment was signed or settled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
