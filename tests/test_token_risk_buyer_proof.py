"""Regression checks for the no-spend AgentServices buyer proof."""

import base64
import importlib.util
import json
from pathlib import Path


EXAMPLE_PATH = Path(__file__).resolve().parents[1] / "examples" / "token_risk_buyer_proof.py"
SPEC = importlib.util.spec_from_file_location("token_risk_buyer_proof", EXAMPLE_PATH)
assert SPEC and SPEC.loader
proof = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(proof)


def test_decodes_x402_payment_required_header_without_padding():
    challenge = {
        "resource": {"url": "https://api.agentservices.to/v1/token-risk/BTC"},
        "accepts": [{"scheme": "exact", "network": "eip155:8453", "maxAmountRequired": "30000"}],
    }
    encoded = base64.b64encode(json.dumps(challenge).encode("utf-8")).decode("ascii").rstrip("=")

    decoded = proof.decode_payment_required({"Payment-Required": encoded})

    assert decoded == challenge
    assert proof.first_requirement(decoded)["maxAmountRequired"] == "30000"
    assert proof.format_usdc("30000") == "0.030000 USDC"


def test_payment_header_lookup_is_case_insensitive():
    assert proof.header_value({"PAYMENT-REQUIRED": "challenge"}, "payment-required") == "challenge"
