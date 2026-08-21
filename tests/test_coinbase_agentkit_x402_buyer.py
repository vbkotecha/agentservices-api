"""Regression checks for the Coinbase AgentKit buyer adapter."""

import base64
import importlib.util
import json
from pathlib import Path


EXAMPLE_PATH = Path(__file__).resolve().parents[1] / "examples" / "coinbase_agentkit_x402_buyer.py"
SPEC = importlib.util.spec_from_file_location("coinbase_agentkit_x402_buyer", EXAMPLE_PATH)
assert SPEC and SPEC.loader
buyer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(buyer)


def test_decodes_padded_and_unpadded_x402_challenge():
    challenge = {
        "x402Version": 2,
        "resource": {"url": "https://api.agentservices.to/v1/token-risk/BTC"},
        "accepts": [{"scheme": "exact", "network": "eip155:8453", "amount": "30000"}],
    }
    encoded = base64.b64encode(json.dumps(challenge).encode()).decode().rstrip("=")

    assert buyer.decode_payment_required(encoded) == challenge
    assert buyer.amount_atomic(challenge) == 30000
    assert buyer.format_usdc(30000) == "0.030000 USDC"


def test_payment_confirmation_is_required(monkeypatch, tmp_path, capsys):
    challenge = {
        "accepts": [{"scheme": "exact", "network": "eip155:8453", "amount": "30000"}]
    }
    encoded = base64.b64encode(json.dumps(challenge).encode()).decode()
    monkeypatch.setattr(buyer, "fetch_challenge", lambda url: (encoded, challenge))
    monkeypatch.setattr(
        buyer,
        "run_agentkit_payment",
        lambda url: (_ for _ in ()).throw(AssertionError("payment must not run")),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["buyer", "--pay", "--url", "https://api.agentservices.to/v1/token-risk/BTC", "--evidence-dir", str(tmp_path)],
    )

    assert buyer.main() == 1
    assert "--confirm-payment" in capsys.readouterr().err
    assert not (tmp_path / "paid-result.json").exists()


def test_challenge_mode_retains_buyer_evidence(monkeypatch, tmp_path, capsys):
    challenge = {
        "accepts": [{"scheme": "exact", "network": "eip155:8453", "amount": "30000"}]
    }
    encoded = base64.b64encode(json.dumps(challenge).encode()).decode()
    monkeypatch.setattr(buyer, "fetch_challenge", lambda url: (encoded, challenge))
    monkeypatch.setattr(
        "sys.argv",
        ["buyer", "--challenge", "--evidence-dir", str(tmp_path)],
    )

    assert buyer.main() == 0
    assert (tmp_path / "payment-required.txt").read_text().strip() == encoded
    assert json.loads((tmp_path / "payment-required.json").read_text()) == challenge
    assert "NO PAYMENT" in capsys.readouterr().out
