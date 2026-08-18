"""Google OAuth + JWT access tokens for MCP (ChatGPT / Claude connectors)."""
import base64
import hashlib
import hmac
import json
import secrets
import time
import urllib.parse
from typing import Any

import requests

from human_billing.config import (
    google_client_id,
    google_client_secret,
    oauth_enabled,
    oauth_jwt_secret,
    public_base_url,
)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

OAUTH_SCOPES = "openid email profile"
TOKEN_TTL_SECONDS = 3600 * 24 * 30  # 30 days


def authorization_server_metadata() -> dict[str, Any]:
    base = public_base_url()
    if not oauth_enabled():
        return {
            "issuer": base,
            "authorization_endpoint": None,
            "token_endpoint": None,
            "response_types_supported": [],
            "grant_types_supported": [],
            "note": "Human billing door disabled. Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and OAUTH_JWT_SECRET.",
        }

    return {
        "issuer": base,
        "authorization_endpoint": f"{base}/oauth/authorize",
        "token_endpoint": f"{base}/oauth/token",
        "registration_endpoint": f"{base}/oauth/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256", "plain"],
        "token_endpoint_auth_methods_supported": ["client_secret_post", "none"],
        "scopes_supported": ["openid", "profile", "email", "mcp"],
    }


def protected_resource_metadata() -> dict[str, Any]:
    base = public_base_url()
    if not oauth_enabled():
        return {
            "resource": f"{base}/mcp",
            "authorization_servers": [],
            "bearer_methods_supported": [],
            "resource_documentation": f"{base}/docs",
            "resource_name": "AgentServices MCP Server",
            "resource_description": "Free tools require no auth. Paid tools use x402 (HTTP 402) payment.",
        }

    return {
        "resource": f"{base}/mcp",
        "authorization_servers": [base],
        "bearer_methods_supported": ["header"],
        "scopes_supported": ["openid", "profile", "email", "mcp"],
        "resource_documentation": f"{base}/docs",
        "resource_name": "AgentServices MCP Server",
        "resource_description": (
            "Google OAuth for human users in ChatGPT/Claude. "
            "Paid MCP tools deduct prepaid Stripe credits; wallet agents still use x402 on REST."
        ),
    }


def google_redirect_uri() -> str:
    return f"{public_base_url()}/oauth/google/callback"


def build_google_auth_url(*, state: str) -> str:
    params = {
        "client_id": google_client_id(),
        "redirect_uri": google_redirect_uri(),
        "response_type": "code",
        "scope": OAUTH_SCOPES,
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_google_code(code: str) -> dict[str, Any]:
    resp = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": google_client_id(),
            "client_secret": google_client_secret(),
            "redirect_uri": google_redirect_uri(),
            "grant_type": "authorization_code",
        },
        timeout=15,
    )
    resp.raise_for_status()
    tokens = resp.json()
    user_resp = requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        timeout=15,
    )
    user_resp.raise_for_status()
    profile = user_resp.json()
    return {
        "sub": profile["sub"],
        "email": profile.get("email", ""),
        "name": profile.get("name", ""),
    }


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(user: dict[str, Any], *, client_id: str = "") -> str:
    now = int(time.time())
    payload = {
        "sub": user["sub"],
        "email": user.get("email", ""),
        "name": user.get("name", ""),
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
        "iss": public_base_url(),
        "aud": "agentservices-mcp",
        "client_id": client_id,
    }
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()
    sig = hmac.new(oauth_jwt_secret().encode(), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(sig)}"


def verify_access_token(token: str) -> dict[str, Any] | None:
    if not oauth_enabled() or not token:
        return None
    parts = token.split(".")
    if len(parts) != 3:
        return None
    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected = hmac.new(oauth_jwt_secret().encode(), signing_input, hashlib.sha256).digest()
    try:
        actual = _b64url_decode(sig_b64)
    except Exception:
        return None
    if not hmac.compare_digest(expected, actual):
        return None
    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception:
        return None
    if payload.get("exp", 0) < time.time():
        return None
    if payload.get("aud") != "agentservices-mcp":
        return None
    return payload


def extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def new_state() -> str:
    return secrets.token_urlsafe(32)


def verify_pkce(code_challenge: str, code_challenge_method: str, code_verifier: str) -> bool:
    """Verify PKCE per RFC 7636. If challenge was sent, verifier is mandatory."""
    if not code_challenge:
        return True
    if not code_verifier:
        return False

    method = (code_challenge_method or "S256").upper()
    if method == "S256":
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        return hmac.compare_digest(expected, code_challenge)
    if method == "PLAIN":
        return hmac.compare_digest(code_verifier, code_challenge)
    return False
