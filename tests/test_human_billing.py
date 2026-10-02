"""Regression tests for the retired Stripe/OAuth MCP billing integration."""
import base64
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))


@pytest.fixture()
def client():
    modules = [
        name for name in list(sys.modules)
        if name in ("main", "index", "mcp_endpoint", "discovery_surfaces")
    ]
    for name in modules:
        sys.modules.pop(name, None)

    env = {
        "VERCEL": "1",
        "CDP_API_KEY_ID": "",
        "CDP_API_KEY_SECRET": "",
        # Old credentials must not turn retired OAuth or billing back on.
        "GOOGLE_CLIENT_ID": "retired-client",
        "GOOGLE_CLIENT_SECRET": "retired-secret",
        "OAUTH_JWT_SECRET": "retired-secret",
        "STRIPE_SECRET_KEY": "sk_test_retired",
        "STRIPE_WEBHOOK_SECRET": "whsec_retired",
        "PUBLIC_BASE_URL": "https://agentservices.to",
    }
    with patch.dict(os.environ, env, clear=False):
        from main import app
        yield TestClient(app)


def _decode_payment_header(headers) -> dict:
    raw = headers.get("payment-required") or headers.get("Payment-Required")
    assert raw
    return json.loads(base64.b64decode(raw))


def test_checkout_webhook_and_oauth_routes_are_absent(client):
    for path in (
        "/billing/checkout",
        "/billing/webhook",
        "/oauth/register",
        "/oauth/authorize",
        "/oauth/google/callback",
        "/oauth/token",
        "/.well-known/oauth-authorization-server",
        "/.well-known/oauth-protected-resource",
    ):
        response = client.post(path) if path in {
            "/billing/checkout",
            "/billing/webhook",
            "/oauth/register",
            "/oauth/token",
        } else client.get(path)
        assert response.status_code == 404, (path, response.text)


def test_credit_purchase_tools_are_absent(client):
    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
    )
    assert response.status_code == 200
    names = {tool["name"] for tool in response.json()["result"]["tools"]}
    assert "buy_credits" not in names
    assert "credit_balance" not in names


def test_paid_mcp_tool_is_refused_even_with_retired_oauth_credentials(client):
    with patch("mcp_endpoint._execute_tool", new_callable=AsyncMock) as execute_tool:
        response = client.post(
            "/mcp",
            headers={"Authorization": "Bearer ignored-retired-token"},
            json={
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {
                    "name": "technical_indicators",
                    "arguments": {"symbol": "BTC"},
                },
            },
        )

    assert response.status_code == 402
    error = response.json()["error"]
    assert "not available through MCP" in error["message"]
    assert "x402" in error["message"]
    assert error["data"]["payment_protocol"] == "x402"
    assert error["data"]["currency"] == "USDC"
    assert "REST" in error["data"]["instructions"]
    execute_tool.assert_not_awaited()


def test_free_mcp_tool_remains_available_without_auth(client):
    with patch(
        "mcp_endpoint._execute_tool",
        new_callable=AsyncMock,
        return_value={"symbol": "BTC", "price": 100},
    ):
        response = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 8,
                "method": "tools/call",
                "params": {"name": "crypto_prices", "arguments": {}},
            },
        )
    assert response.status_code == 200
    assert "result" in response.json()


def test_x402_unpaid_rest_still_returns_payment_required(client):
    response = client.get("/v1/fx")
    assert response.status_code == 402, response.text
    payload = _decode_payment_header(response.headers)
    assert payload.get("x402Version") == 2


def test_health_no_longer_advertises_oauth_or_credit_billing(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["x402_enabled"] is True
    assert "oauth_enabled" not in data
    assert "credits_enabled" not in data
    assert "billing_ledger" not in data