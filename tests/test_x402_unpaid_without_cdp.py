"""Unpaid x402 routes must return 402 when CDP facilitator keys are unset."""
import base64
import importlib
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))


def _decode_payment_header(headers) -> dict:
    raw = headers.get("payment-required") or headers.get("Payment-Required")
    assert raw
    return json.loads(base64.b64decode(raw))


def _fresh_import(module_name: str):
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


@pytest.fixture()
def client_without_cdp_keys():
    modules_to_clear = [
        name
        for name in list(sys.modules)
        if name in ("main", "index", "x402_payment") or name.startswith(("crypto_data", "agent_memory", "geo_data", "web_data"))
    ]
    for name in modules_to_clear:
        sys.modules.pop(name, None)

    env = {
        "VERCEL": "1",
        "CDP_API_KEY_ID": "",
        "CDP_API_KEY_SECRET": "",
    }
    with patch.dict(os.environ, env, clear=False):
        from main import app

        yield TestClient(app)


def test_unpaid_fx_returns_402_without_cdp_keys(client_without_cdp_keys):
    response = client_without_cdp_keys.get("/v1/fx")
    assert response.status_code == 402, response.text
    payload = _decode_payment_header(response.headers)
    assert payload.get("x402Version") == 2
    accepts = payload.get("accepts") or []
    base_option = next(item for item in accepts if item.get("network") == "eip155:8453")
    assert base_option.get("scheme") == "exact"


def test_unpaid_fx_returns_402_when_create_cdp_auth_headers_raises(client_without_cdp_keys):
    def raise_missing_keys():
        raise ValueError("CDP_API_KEY_ID and CDP_API_KEY_SECRET must be set")

    with patch("x402_payment.create_cdp_auth_headers", side_effect=raise_missing_keys):
        response = client_without_cdp_keys.get("/v1/fx")
    assert response.status_code == 402, response.text
    payload = _decode_payment_header(response.headers)
    assert payload.get("x402Version") == 2
    accepts = payload.get("accepts") or []
    assert any(item.get("network") == "eip155:8453" for item in accepts)


def test_x402_payment_import_survives_permission_error_on_root():
    original_exists = Path.exists

    def permission_exists(self):
        if self.as_posix().startswith("/root/.letta"):
            raise PermissionError(13, "Permission denied")
        return original_exists(self)

    for name in list(sys.modules):
        if name in ("main", "index", "x402_payment", "letta_keys"):
            sys.modules.pop(name, None)

    env = {
        "VERCEL": "1",
        "CDP_API_KEY_ID": "",
        "CDP_API_KEY_SECRET": "",
    }
    with patch.dict(os.environ, env, clear=False), patch.object(Path, "exists", permission_exists):
        x402_payment = _fresh_import("x402_payment")
        assert x402_payment.CDP_API_KEY == ""
        assert x402_payment.CDP_API_SECRET == ""
        assert x402_payment.cdp_auth_available() is False

        index_module = importlib.import_module("index")
        response = TestClient(index_module.app).get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        fx_response = TestClient(index_module.app).get("/v1/fx")
        assert fx_response.status_code == 402
