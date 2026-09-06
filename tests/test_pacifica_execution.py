"""Trade API — Pacifica venue door: policy, forward, paper, market_type, path wiring."""
import importlib
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

PRINCIPAL = "42trU9A5ExamplePacificaAccountAddress"
TRADE_PAC_ORDER = "/v1/trade/pacifica/order"
TRADE_PAC_BOOTSTRAP = "/v1/trade/pacifica/bootstrap"
TRADE_PAC_PAPER = "/v1/trade/pacifica/paper/order"
TRADE_PAC_EVAL = "/v1/trade/pacifica/eval/order"

SIGNED_CREATE_ORDER = {
    "operation": "create_order",
    "request": {
        "account": PRINCIPAL,
        "signature": "5j1Vy9UqExampleSignature",
        "timestamp": 1716200000000,
        "symbol": "BTC",
        "price": "50000",
        "amount": "0.01",
        "side": "bid",
        "tif": "GTC",
        "reduce_only": False,
        "agent_wallet": "69trU9A5ExampleAgentWallet",
    },
}

PAC_OK = {"order_id": 99901}


def _fresh_pac_module():
    for name in list(sys.modules):
        if name == "pacifica_data" or name.startswith("pacifica_data."):
            sys.modules.pop(name, None)
    return importlib.import_module("pacifica_data")


@pytest.fixture()
def pac_mod(tmp_path):
    mod = _fresh_pac_module()
    with patch.object(mod, "_policy_dir", return_value=tmp_path):
        yield mod


@pytest.fixture()
def client():
    for name in list(sys.modules):
        if name in ("main", "index", "pacifica_data") or name.startswith("pacifica_data"):
            sys.modules.pop(name, None)
    from main import app

    return TestClient(app)


def test_bootstrap_documents_agent_sign_model(client):
    resp = client.get(TRADE_PAC_BOOTSTRAP)
    assert resp.status_code == 200
    body = resp.json()
    assert body["venue_api_keys"] == "never_collected"
    assert body["x402"] == "not_used_on_execution_path"
    assert body["base_path"] == "/v1/trade/pacifica"
    assert body["model"] == "agent_sign_only"
    assert "bind_agent_wallet" in body["human_bootstrap"][1]
    assert set(body["market_types"]["accepted"]) == {"spot", "perp", "future"}
    assert set(body["market_types"]["supported_now"]) == {"spot", "perp"}


def test_over_cap_order_rejected(pac_mod):
    pac_mod.set_policy(
        pac_mod.PacificaExecutionPolicy(principal=PRINCIPAL, max_notional_usd=100.0, allowed_coins=["BTC"])
    )
    req = pac_mod.PacificaForwardRequest(
        principal=PRINCIPAL,
        signed=pac_mod.SignedPacificaPayload(**SIGNED_CREATE_ORDER),
    )
    with pytest.raises(HTTPException) as exc:
        pac_mod.forward_signed_action(req)
    assert exc.value.status_code == 403
    assert exc.value.detail["error"] == "max_notional_exceeded"


def test_disallowed_coin_rejected(pac_mod):
    pac_mod.set_policy(
        pac_mod.PacificaExecutionPolicy(principal=PRINCIPAL, max_notional_usd=1_000_000, allowed_coins=["ETH"])
    )
    req = pac_mod.PacificaForwardRequest(
        principal=PRINCIPAL,
        signed=pac_mod.SignedPacificaPayload(**SIGNED_CREATE_ORDER),
    )
    with pytest.raises(HTTPException) as exc:
        pac_mod.forward_signed_action(req)
    assert exc.value.status_code == 403
    assert exc.value.detail["error"] == "coin_not_allowlisted"


def test_allowed_order_forwarded(pac_mod):
    pac_mod.set_policy(
        pac_mod.PacificaExecutionPolicy(principal=PRINCIPAL, max_notional_usd=10_000, allowed_coins=["BTC"])
    )
    req = pac_mod.PacificaForwardRequest(
        principal=PRINCIPAL,
        signed=pac_mod.SignedPacificaPayload(**SIGNED_CREATE_ORDER),
    )
    mock_resp = MagicMock()
    mock_resp.json.return_value = PAC_OK
    with patch("pacifica_data.requests.post", return_value=mock_resp) as post:
        result = pac_mod.forward_signed_action(req)
    assert post.called
    sent = post.call_args[1]["json"]
    assert "builder_code" not in sent
    assert result["receipt"]["order_id"] == 99901
    assert result["receipt"]["orders"][0]["coin"] == "BTC"
    assert result["receipt"]["orders"][0]["side"] == "buy"
    assert result["market_type"] == "perp"


def test_http_allowed_order_forwarded(client, tmp_path):
    pac_mod = _fresh_pac_module()
    with patch.object(pac_mod, "_policy_dir", return_value=tmp_path):
        pac_mod.set_policy(
            pac_mod.PacificaExecutionPolicy(principal=PRINCIPAL, max_notional_usd=10_000, allowed_coins=["BTC"])
        )
    mock_resp = MagicMock()
    mock_resp.json.return_value = PAC_OK
    with patch("pacifica_data.requests.post", return_value=mock_resp):
        resp = client.post(
            TRADE_PAC_ORDER,
            json={"principal": PRINCIPAL, "signed": SIGNED_CREATE_ORDER, "market_type": "perp"},
        )
    assert resp.status_code == 200
    assert resp.json()["receipt"]["order_id"] == 99901


def test_trade_order_path_not_behind_x402(client):
    resp = client.post(
        TRADE_PAC_ORDER,
        json={"principal": PRINCIPAL, "signed": SIGNED_CREATE_ORDER},
    )
    assert resp.status_code != 402


def test_eval_pass_fail(pac_mod):
    pac_mod.set_policy(
        pac_mod.PacificaExecutionPolicy(principal=PRINCIPAL, max_notional_usd=500, allowed_coins=["BTC"])
    )
    fail = pac_mod.eval_order_against_policy(PRINCIPAL, "BTC", "buy", 0.1, 50_000)
    assert fail["pass"] is False
    pass_result = pac_mod.eval_order_against_policy(PRINCIPAL, "BTC", "buy", 0.001, 50_000)
    assert pass_result["pass"] is True


def test_paper_order_simulated(client):
    resp = client.post(
        TRADE_PAC_PAPER,
        json={"coin": "ETH", "side": "sell", "size": 0.5, "price": 3000, "market_type": "perp"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["receipt"]["simulated"] is True
    assert body["receipt"]["coin"] == "ETH"
    assert body["receipt"]["market_type"] == "perp"


def test_no_venue_api_key_collection_in_pacifica_module():
    path = SRC / "pacifica_data.py"
    text = path.read_text()
    forbidden_patterns = [
        r"os\.environ\.get\([\"'].*API_KEY",
        r"os\.environ\[[\"'].*API_KEY",
        r"private_key\s*=",
        r"secret_key\s*=",
        r"exchange_api_key",
        r"PACIFICA_API_KEY",
        r"PAC_API_KEY",
    ]
    hits = [pat for pat in forbidden_patterns if re.search(pat, text, re.IGNORECASE)]
    assert hits == [], f"Forbidden key-collection patterns found: {hits}"


def test_openapi_lists_trade_pacifica_routes(client):
    schema = client.get("/openapi.json").json()
    paths = schema.get("paths", {})
    assert TRADE_PAC_ORDER in paths
    assert TRADE_PAC_PAPER in paths
    assert TRADE_PAC_EVAL in paths
    assert "/v1/trade/pacifica/order/{order_id}" in paths
    order_post = paths[TRADE_PAC_ORDER]["post"]
    assert "Trade" in order_post.get("tags", [])


def test_mcp_tools_include_trade_pacifica():
    from mcp_endpoint import MCP_TOOLS

    names = {t["name"] for t in MCP_TOOLS}
    for expected in (
        "trade_pacifica_order",
        "trade_pacifica_cancel",
        "trade_pacifica_order_status",
        "trade_pacifica_get_policy",
        "trade_pacifica_set_policy",
        "trade_pacifica_paper_order",
        "trade_pacifica_eval_order",
    ):
        assert expected in names


def test_kill_switch_blocks_orders(pac_mod):
    pac_mod.set_policy(
        pac_mod.PacificaExecutionPolicy(principal=PRINCIPAL, kill_switch=True, allowed_coins=["BTC"])
    )
    req = pac_mod.PacificaForwardRequest(
        principal=PRINCIPAL,
        signed=pac_mod.SignedPacificaPayload(**SIGNED_CREATE_ORDER),
    )
    with pytest.raises(HTTPException) as exc:
        pac_mod.forward_signed_action(req)
    assert exc.value.status_code == 403
    assert exc.value.detail["error"] == "kill_switch_active"


def test_invalid_market_type_rejected(pac_mod):
    with pytest.raises(HTTPException) as exc:
        pac_mod.validate_market_type("options")
    assert exc.value.status_code == 400
    assert exc.value.detail["error"] == "invalid_market_type"


def test_future_market_type_not_supported_on_pacifica(pac_mod):
    with pytest.raises(HTTPException) as exc:
        pac_mod.validate_market_type("future")
    assert exc.value.status_code == 422
    assert exc.value.detail["error"] == "market_type_not_supported"
    assert exc.value.detail["venue"] == "pacifica"


def test_spot_market_type_accepted(pac_mod):
    assert pac_mod.validate_market_type("spot") == "spot"


def test_http_invalid_market_type_rejected(client):
    resp = client.post(
        TRADE_PAC_ORDER,
        json={"principal": PRINCIPAL, "signed": SIGNED_CREATE_ORDER, "market_type": "options"},
    )
    assert resp.status_code == 422


def test_http_future_market_type_rejected(client, tmp_path):
    pac_mod = _fresh_pac_module()
    with patch.object(pac_mod, "_policy_dir", return_value=tmp_path):
        pac_mod.set_policy(
            pac_mod.PacificaExecutionPolicy(principal=PRINCIPAL, max_notional_usd=10_000, allowed_coins=["BTC"])
        )
    resp = client.post(
        TRADE_PAC_ORDER,
        json={"principal": PRINCIPAL, "signed": SIGNED_CREATE_ORDER, "market_type": "future"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"]["error"] == "market_type_not_supported"


def test_order_status_by_path(client):
    mock_status = {"success": True, "data": [{"order_id": 12345, "order_status": "open"}]}
    with patch("pacifica_data.requests.get") as get:
        get.return_value = MagicMock(json=lambda: mock_status, raise_for_status=lambda: None)
        resp = client.get(
            "/v1/trade/pacifica/order/12345",
            params={"user": PRINCIPAL},
        )
    assert resp.status_code == 200
    assert resp.json() == mock_status


def test_cancel_forwarded(pac_mod):
    pac_mod.set_policy(
        pac_mod.PacificaExecutionPolicy(principal=PRINCIPAL, allowed_coins=["BTC"])
    )
    signed = {
        "operation": "cancel_order",
        "request": {
            "account": PRINCIPAL,
            "signature": "sig",
            "timestamp": 1716200000000,
            "symbol": "BTC",
            "order_id": 123,
        },
    }
    req = pac_mod.PacificaForwardRequest(
        principal=PRINCIPAL,
        signed=pac_mod.SignedPacificaPayload(**signed),
    )
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"success": True}
    with patch("pacifica_data.requests.post", return_value=mock_resp) as post:
        result = pac_mod.forward_signed_action(req)
    assert post.called
    assert post.call_args[0][0].endswith("/api/v1/orders/cancel")
    assert result["receipt"]["operation"] == "cancel_order"
