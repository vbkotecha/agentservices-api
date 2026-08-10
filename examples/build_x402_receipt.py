#!/usr/bin/env python3
"""Build a buyer-retained receipt from an x402 challenge and successful paid result.

This utility never signs or submits a payment. Give it the original HTTP 402
`payment-required` value plus the response body from the paid retry. It emits a
portable JSON receipt that binds the quoted payment terms to the delivered result.

Usage:
  python3 examples/build_x402_receipt.py \
    --payment-required-file /path/to/payment-required.txt \
    --result-file /path/to/paid-result.json \
    --payment-proof tx-or-authorization-reference
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def decode_payment_required(value: str) -> dict[str, Any]:
    """Decode an x402 v2 base64url payment-required header value."""
    padding = "=" * (-len(value) % 4)
    return json.loads(base64.urlsafe_b64decode(value + padding).decode("utf-8"))


def first_requirement(challenge: dict[str, Any]) -> dict[str, Any]:
    requirements = challenge.get("accepts") or challenge.get("paymentRequirements") or []
    if not requirements:
        raise ValueError("payment-required challenge has no accepted requirement")
    return requirements[0]


def canonical_json_digest(value: Any) -> str:
    payload = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def build_receipt(
    payment_required: str,
    paid_result: Any,
    payment_proof: str,
    received_at: str | None = None,
) -> dict[str, Any]:
    """Create a receipt from buyer-held evidence; does not assert chain settlement."""
    challenge = decode_payment_required(payment_required.strip())
    requirement = first_requirement(challenge)
    resource = challenge.get("resource") or {}
    amount = requirement.get("maxAmountRequired") or requirement.get("amount")
    if not resource.get("url") or amount is None or not payment_proof.strip():
        raise ValueError("challenge URL, requirement amount, and payment proof are required")

    return {
        "receipt_version": "agentservices.x402-receipt.v1",
        "resource": resource["url"],
        "quoted_payment": {
            "scheme": requirement.get("scheme"),
            "network": requirement.get("network"),
            "asset": requirement.get("asset"),
            "max_amount_required": str(amount),
            "pay_to": requirement.get("payTo"),
        },
        "payment_proof": payment_proof.strip(),
        "payment_required_digest": canonical_json_digest(challenge),
        "result_digest": canonical_json_digest(paid_result),
        "received_at": received_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "settlement_note": "Buyer-retained evidence. Verify settlement with the selected x402 wallet or facilitator before treating it as final.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payment-required-file", type=Path, required=True)
    parser.add_argument("--result-file", type=Path, required=True)
    parser.add_argument("--payment-proof", required=True)
    parser.add_argument("--received-at")
    args = parser.parse_args()

    receipt = build_receipt(
        args.payment_required_file.read_text(encoding="utf-8"),
        json.loads(args.result_file.read_text(encoding="utf-8")),
        args.payment_proof,
        args.received_at,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
