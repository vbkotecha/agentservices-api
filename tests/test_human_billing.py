"""Tests for human billing door: Stripe credits, OAuth discovery, PKCE, webhook, x402 unchanged."""
import base64
import hashlib
import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))


def _decode_payment_header(headers) -> dict:
    raw = headers.get("payment-required") or headers.get("Payment-Required")
    assert raw
    return json.loads(base64.b64decode(raw))


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class MockStripeStore:
    """In-memory Stripe Customer Balance mock for tests."""

    def __init__(self):
        self.customers: dict[str, dict] = {}
        self.by_sub: dict[str, str] = {}
        self.balance_txns: list[dict] = []
        self.idempotency_keys: set[str] = set()
        self._next_id = 1

    def _new_id(self, prefix: str) -> str:
        cid = f"{prefix}_{self._next_id}"
        self._next_id += 1
        return cid

    def find_or_create_customer(self, *, google_sub: str, email: str = "") -> dict:
        if google_sub in self.by_sub:
            return self.customers[self.by_sub[google_sub]]
        cid = self._new_id("cus")
        customer = {"id": cid, "metadata": {"google_sub": google_sub}, "balance": 0}
        if email:
            customer["email"] = email
        self.customers[cid] = customer
        self.by_sub[google_sub] = cid
        return customer

    def search_customers(self, query: str, limit: int = 1) -> dict:
        marker = 'metadata["google_sub"]:"'
        if marker in query:
            sub = query.split(marker, 1)[1].split('"', 1)[0]
            if sub in self.by_sub:
                return {"data": [self.customers[self.by_sub[sub]]]}
        return {"data": []}

    def create_balance_transaction(self, customer_id: str, *, amount: int, currency: str, **kwargs):
        key = kwargs.get("idempotency_key")
        if key and key in self.idempotency_keys:
            return {"id": "txn_dup", "amount": amount}
        if key:
            self.idempotency_keys.add(key)

        customer = self.customers[customer_id]
        customer["balance"] = (customer.get("balance") or 0) + amount
        txn = {"id": self._new_id("txn"), "customer": customer_id, "amount": amount, **kwargs}
        self.balance_txns.append(txn)
        return txn

    def build_mock_stripe(self):
        store = self
        mock_stripe = MagicMock()

        def customer_search(**kwargs):
            return store.search_customers(kwargs.get("query", ""), kwargs.get("limit", 1))

        def customer_create(**kwargs):
            sub = (kwargs.get("metadata") or {}).get("google_sub", "")
            email = kwargs.get("email", "")
            if sub:
                return store.find_or_create_customer(google_sub=sub, email=email)
            cid = store._new_id("cus")
            customer = {"id": cid, "metadata": kwargs.get("metadata") or {}, "balance": 0}
            if email:
                customer["email"] = email
            store.customers[cid] = customer
            return customer

        def customer_retrieve(customer_id):
            return store.customers[customer_id]

        def customer_modify(customer_id, **kwargs):
            customer = store.customers[customer_id]
            if "metadata" in kwargs:
                customer["metadata"] = {**customer.get("metadata", {}), **kwargs["metadata"]}
            return customer

        def create_balance_txn(customer_id, **kwargs):
            return store.create_balance_transaction(customer_id, **kwargs)

        mock_stripe.Customer.search.side_effect = customer_search
        mock_stripe.Customer.create.side_effect = customer_create
        mock_stripe.Customer.retrieve.side_effect = customer_retrieve
        mock_stripe.Customer.modify.side_effect = customer_modify
        mock_stripe.Customer.create_balance_transaction.side_effect = create_balance_txn

        session_holder = {}

        def checkout_create(**kwargs):
            sid = store._new_id("cs")
            session = {
                "id": sid,
                "url": f"https://checkout.stripe.com/{sid}",
                "customer": kwargs.get("customer"),
            }
            session_holder[sid] = session
            return session

        mock_stripe.checkout.Session.create.side_effect = checkout_create
        mock_stripe.Webhook.construct_event = MagicMock()
        return mock_stripe


@pytest.fixture()
def stripe_store():
    return MockStripeStore()


@pytest.fixture()
def human_billing_env(stripe_store):
    env = {
        "VERCEL": "1",
        "CDP_API_KEY_ID": "",
        "CDP_API_KEY_SECRET": "",
        "GOOGLE_CLIENT_ID": "test-google-client-id",
        "GOOGLE_CLIENT_SECRET": "test-google-secret",
        "OAUTH_JWT_SECRET": "test-jwt-secret-for-human-billing",
        "STRIPE_SECRET_KEY": "sk_test_fake",
        "STRIPE_WEBHOOK_SECRET": "whsec_test_fake",
        "PUBLIC_BASE_URL": "https://agentservices.to",
    }
    modules = [
        name for name in list(sys.modules)
        if name in ("main", "index", "mcp_endpoint", "human_billing.config", "human_billing.credits",
                     "human_billing.oauth", "human_billing.router", "human_billing.stripe_billing")
        or name.startswith("human_billing")
    ]
    for name in modules:
        sys.modules.pop(name, None)

    mock_stripe = stripe_store.build_mock_stripe()
    with patch.dict(os.environ, env, clear=False), patch(
        "human_billing.stripe_billing._stripe", return_value=mock_stripe
    ):
        yield env


@pytest.fixture()
def client(human_billing_env):
    from main import app
    return TestClient(app)


@pytest.fixture()
def auth_token(human_billing_env):
    from human_billing.oauth import create_access_token
    return create_access_token({"sub": "google-user-123", "email": "test@example.com", "name": "Test"})


def test_stripe_credit_roundtrip(stripe_store, human_billing_env):
    from human_billing.credits import credit_balance, get_balance, debit_balance

    credit_balance("user-roundtrip", Decimal("5"), reference="ref-1", source="test")
    assert get_balance("user-roundtrip") == Decimal("5")
    debit_balance("user-roundtrip", Decimal("0.01"), tool="web_search")
    assert get_balance("user-roundtrip") == Decimal("4.99")


def test_credit_deduct_on_paid_mcp_tool(client, auth_token, human_billing_env):
    from human_billing.credits import credit_balance

    credit_balance("google-user-123", Decimal("1.00"), reference="setup", source="test")

    with patch("crypto_data.get_indicators", return_value={"symbol": "BTC", "rsi": 55}):
        response = client.post(
            "/mcp",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
                "name": "technical_indicators",
                "arguments": {"symbol": "BTC"},
            }},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "result" in body, body

    from human_billing.credits import get_balance
    balance = get_balance("google-user-123")
    assert balance == Decimal("0.98")


def test_failed_tool_does_not_debit(client, auth_token, human_billing_env):
    from human_billing.credits import credit_balance, get_balance

    credit_balance("google-user-123", Decimal("1.00"), reference="setup2", source="test")

    with patch("crypto_data.get_indicators", return_value={"error": "upstream failed"}):
        response = client.post(
            "/mcp",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": {
                "name": "technical_indicators",
                "arguments": {"symbol": "BTC"},
            }},
        )

    assert response.status_code == 200, response.text
    text = response.json()["result"]["content"][0]["text"]
    assert "upstream failed" in text
    assert get_balance("google-user-123") == Decimal("1.00")


def test_web_search_tool_exists_and_is_billed(client, auth_token, human_billing_env):
    from human_billing.credits import credit_balance, get_balance

    tools = client.post("/mcp", json={"jsonrpc": "2.0", "id": 20, "method": "tools/list"}).json()
    tool_names = [t["name"] for t in tools["result"]["tools"]]
    assert "web_search" in tool_names

    credit_balance("google-user-123", Decimal("1.00"), reference="setup3", source="test")

    with patch("search_data.web_search", return_value={"query": "btc", "results": [{"title": "BTC"}]}):
        response = client.post(
            "/mcp",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"jsonrpc": "2.0", "id": 21, "method": "tools/call", "params": {
                "name": "web_search",
                "arguments": {"q": "btc etf"},
            }},
        )

    assert response.status_code == 200, response.text
    assert get_balance("google-user-123") == Decimal("0.99")


def test_insufficient_credits_returns_checkout_url(client, auth_token, human_billing_env):
    with patch("human_billing.stripe_billing.create_checkout_session") as mock_checkout:
        mock_checkout.return_value = {
            "checkout_url": "https://checkout.stripe.com/test-session",
            "session_id": "cs_test_123",
        }
        response = client.post(
            "/mcp",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
                "name": "technical_indicators",
                "arguments": {"symbol": "BTC"},
            }},
        )

    assert response.status_code == 402, response.text
    body = response.json()
    assert body["error"]["code"] == -32001
    assert "checkout.stripe.com" in body["error"]["data"]["checkout_url"]
    assert body["error"]["data"]["required_usd"] == "0.02"


def test_pkce_rejects_missing_verifier(client, human_billing_env):
    from human_billing.oauth import create_authorization_code_token

    verifier = "test-verifier-abc123"
    challenge = _pkce_challenge(verifier)
    auth_code = create_authorization_code_token(
        user={"sub": "pkce-user", "email": "pkce@test.com"},
        client_id="chatgpt",
        redirect_uri="https://chatgpt.com/callback",
        code_challenge=challenge,
        code_challenge_method="S256",
    )

    response = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": "https://chatgpt.com/callback",
        },
    )
    assert response.status_code == 400
    assert "PKCE" in response.json()["detail"]


def test_pkce_rejects_wrong_verifier(client, human_billing_env):
    from human_billing.oauth import create_authorization_code_token

    challenge = _pkce_challenge("correct-verifier")
    auth_code = create_authorization_code_token(
        user={"sub": "pkce-user", "email": "pkce@test.com"},
        client_id="chatgpt",
        redirect_uri="https://chatgpt.com/callback",
        code_challenge=challenge,
        code_challenge_method="S256",
    )

    response = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": "https://chatgpt.com/callback",
            "code_verifier": "wrong-verifier",
        },
    )
    assert response.status_code == 400
    assert "PKCE" in response.json()["detail"]


def test_pkce_accepts_valid_s256_verifier(client, human_billing_env):
    from human_billing.oauth import create_authorization_code_token

    verifier = "valid-verifier-xyz"
    challenge = _pkce_challenge(verifier)
    auth_code = create_authorization_code_token(
        user={"sub": "pkce-user", "email": "pkce@test.com", "name": "PKCE"},
        client_id="chatgpt",
        redirect_uri="https://chatgpt.com/callback",
        code_challenge=challenge,
        code_challenge_method="S256",
    )

    response = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": "https://chatgpt.com/callback",
            "code_verifier": verifier,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["access_token"]


def test_webhook_credits_user(client, stripe_store, human_billing_env):
    from human_billing.credits import get_balance

    mock_event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_webhook_1",
                "payment_status": "paid",
                "metadata": {"google_sub": "google-user-456"},
                "amount_total": 1000,
                "client_reference_id": "google-user-456",
            }
        },
    }

    with patch("human_billing.stripe_billing._stripe") as mock_stripe_factory:
        mock_stripe = stripe_store.build_mock_stripe()
        mock_stripe.Webhook.construct_event.return_value = mock_event
        mock_stripe_factory.return_value = mock_stripe

        response = client.post(
            "/billing/webhook",
            content=b"{}",
            headers={"stripe-signature": "sig_test"},
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "credited"
    assert data["amount_usd"] == "10"
    assert get_balance("google-user-456") == Decimal("10")


def test_webhook_idempotent(client, stripe_store, human_billing_env):
    mock_event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_webhook_dup",
                "payment_status": "paid",
                "metadata": {"google_sub": "google-user-dup"},
                "amount_total": 1000,
            }
        },
    }

    with patch("human_billing.stripe_billing._stripe") as mock_stripe_factory:
        mock_stripe = stripe_store.build_mock_stripe()
        mock_stripe.Webhook.construct_event.return_value = mock_event
        mock_stripe_factory.return_value = mock_stripe

        r1 = client.post("/billing/webhook", content=b"{}", headers={"stripe-signature": "sig"})
        r2 = client.post("/billing/webhook", content=b"{}", headers={"stripe-signature": "sig"})

    assert r1.json()["status"] == "credited"
    assert r2.json()["status"] == "credited"

    from human_billing.credits import get_balance
    assert get_balance("google-user-dup") == Decimal("10")


def test_webhook_ignores_unpaid_session(client, human_billing_env):
    mock_event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_unpaid",
                "payment_status": "unpaid",
                "metadata": {"google_sub": "google-user-unpaid"},
                "amount_total": 1000,
            }
        },
    }

    with patch("human_billing.stripe_billing._stripe") as mock_stripe_factory:
        store = MockStripeStore()
        mock_stripe = store.build_mock_stripe()
        mock_stripe.Webhook.construct_event.return_value = mock_event
        mock_stripe_factory.return_value = mock_stripe

        response = client.post("/billing/webhook", content=b"{}", headers={"stripe-signature": "sig"})

    assert response.json()["status"] == "ignored"
    from human_billing.credits import get_balance
    assert get_balance("google-user-unpaid") == Decimal("0")


def test_x402_unpaid_rest_still_402(client):
    response = client.get("/v1/fx")
    assert response.status_code == 402, response.text
    payload = _decode_payment_header(response.headers)
    assert payload.get("x402Version") == 2


def test_oauth_discovery_endpoints_exist(client, human_billing_env):
    auth_server = client.get("/.well-known/oauth-authorization-server")
    assert auth_server.status_code == 200
    data = auth_server.json()
    assert data["authorization_endpoint"] == "https://agentservices.to/oauth/authorize"
    assert data["token_endpoint"] == "https://agentservices.to/oauth/token"
    assert "authorization_code" in data["grant_types_supported"]

    protected = client.get("/.well-known/oauth-protected-resource")
    assert protected.status_code == 200
    pdata = protected.json()
    assert pdata["resource"] == "https://agentservices.to/mcp"
    assert "https://agentservices.to" in pdata["authorization_servers"]


def test_mcp_well_known_shows_oauth_when_enabled(client, human_billing_env):
    response = client.get("/.well-known/mcp")
    assert response.status_code == 200
    data = response.json()
    assert data["authentication"]["type"] == "oauth2"


def test_free_mcp_tool_works_without_auth(client):
    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
            "name": "fear_greed",
            "arguments": {},
        }},
    )
    assert response.status_code == 200, response.text
    assert "result" in response.json()


def test_credits_enabled_on_vercel_without_redis(human_billing_env, client):
    health = client.get("/health")
    assert health.status_code == 200
    data = health.json()
    assert data["credits_enabled"] is True
    assert data["oauth_enabled"] is True
    assert data.get("billing_ledger") == "stripe_customer_balance"


def test_boot_without_google_stripe():
    modules = [
        name for name in list(sys.modules)
        if name in ("main", "index") or name.startswith("human_billing")
    ]
    for name in modules:
        sys.modules.pop(name, None)

    env = {
        "VERCEL": "1",
        "CDP_API_KEY_ID": "",
        "CDP_API_KEY_SECRET": "",
        "GOOGLE_CLIENT_ID": "",
        "GOOGLE_CLIENT_SECRET": "",
        "STRIPE_SECRET_KEY": "",
    }
    with patch.dict(os.environ, env, clear=False):
        from main import app
        c = TestClient(app)
        health = c.get("/health")
        assert health.status_code == 200
        assert health.json()["oauth_enabled"] is False
        assert health.json()["credits_enabled"] is False
        assert health.json()["x402_enabled"] is True
        fx = c.get("/v1/fx")
        assert fx.status_code == 402
