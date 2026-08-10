import base64
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from build_x402_receipt import build_receipt


def test_build_receipt_binds_quote_and_result_without_claiming_settlement():
    challenge = {
        "resource": {"url": "https://api.agentservices.to/v1/token-risk/bitcoin"},
        "accepts": [{
            "scheme": "exact",
            "network": "eip155:8453",
            "asset": "0xUSDC",
            "maxAmountRequired": "30000",
            "payTo": "0xPayee",
        }],
    }
    encoded = base64.urlsafe_b64encode(json.dumps(challenge).encode()).decode().rstrip("=")
    result = {"token": "bitcoin", "risk_score": 15}

    receipt = build_receipt(encoded, result, "0xtransaction", "2026-08-07T00:00:00Z")

    assert receipt["receipt_version"] == "agentservices.x402-receipt.v1"
    assert receipt["resource"] == challenge["resource"]["url"]
    assert receipt["quoted_payment"]["max_amount_required"] == "30000"
    assert receipt["payment_proof"] == "0xtransaction"
    assert receipt["received_at"] == "2026-08-07T00:00:00Z"
    assert receipt["payment_required_digest"].startswith("sha256:")
    assert receipt["result_digest"].startswith("sha256:")
    assert "Verify settlement" in receipt["settlement_note"]
