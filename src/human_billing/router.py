"""FastAPI routes for OAuth, Stripe billing, and minimal success/cancel pages."""
import urllib.parse
from typing import Any

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from human_billing.config import credits_enabled, oauth_enabled, public_base_url
from human_billing.credits import get_balance
from human_billing.oauth import (
    authorization_server_metadata,
    build_google_auth_url,
    create_access_token,
    create_authorization_code_token,
    create_oauth_state_token,
    exchange_google_code,
    extract_bearer_token,
    protected_resource_metadata,
    verify_access_token,
    verify_authorization_code_token,
    verify_oauth_state_token,
    verify_pkce,
)
from human_billing.stripe_billing import create_checkout_session, handle_webhook

router = APIRouter(tags=["Human Billing"])


@router.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server_well_known():
    return authorization_server_metadata()


@router.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource_well_known():
    return protected_resource_metadata()


@router.post("/oauth/register")
async def oauth_register(request: Request):
    """Minimal dynamic client registration for MCP connectors."""
    if not oauth_enabled():
        raise HTTPException(503, "OAuth is not configured")
    import secrets
    import time

    body = await request.json()
    client_id = secrets.token_urlsafe(16)
    return {
        "client_id": client_id,
        "client_secret": secrets.token_urlsafe(32),
        "client_id_issued_at": int(time.time()),
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "redirect_uris": body.get("redirect_uris", []),
        "token_endpoint_auth_method": "client_secret_post",
    }


@router.get("/oauth/authorize")
async def oauth_authorize(
    response_type: str = "code",
    client_id: str = "",
    redirect_uri: str = "",
    state: str = "",
    scope: str = "openid email profile mcp",
    code_challenge: str = "",
    code_challenge_method: str = "S256",
):
    if not oauth_enabled():
        raise HTTPException(503, "OAuth is not configured")
    if response_type != "code":
        raise HTTPException(400, "Only response_type=code is supported")
    if not redirect_uri:
        raise HTTPException(400, "redirect_uri is required")

    oauth_state = create_oauth_state_token(
        client_id=client_id,
        redirect_uri=redirect_uri,
        state=state,
        scope=scope,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method or "S256",
    )
    return RedirectResponse(build_google_auth_url(state=oauth_state))


@router.get("/oauth/google/callback")
async def oauth_google_callback(code: str = "", state: str = "", error: str = ""):
    if not oauth_enabled():
        raise HTTPException(503, "OAuth is not configured")
    if error:
        raise HTTPException(400, f"Google OAuth error: {error}")

    pending = verify_oauth_state_token(state)
    if not pending:
        raise HTTPException(400, "Invalid or expired OAuth state")

    user = exchange_google_code(code)
    auth_code = create_authorization_code_token(
        user=user,
        client_id=pending.get("client_id", ""),
        redirect_uri=pending.get("redirect_uri", ""),
        code_challenge=pending.get("code_challenge", ""),
        code_challenge_method=pending.get("code_challenge_method", "S256"),
    )

    params = {"code": auth_code}
    if pending.get("state"):
        params["state"] = pending["state"]
    redirect_uri = pending["redirect_uri"]
    sep = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(f"{redirect_uri}{sep}{urllib.parse.urlencode(params)}")


@router.post("/oauth/token")
async def oauth_token(
    grant_type: str = Form("authorization_code"),
    code: str = Form(""),
    redirect_uri: str = Form(""),
    client_id: str = Form(""),
    code_verifier: str = Form(""),
):
    if not oauth_enabled():
        raise HTTPException(503, "OAuth is not configured")
    if grant_type != "authorization_code":
        raise HTTPException(400, "Unsupported grant_type")

    pending = verify_authorization_code_token(code)
    if not pending:
        raise HTTPException(400, "Invalid or expired authorization code")

    if redirect_uri and pending.get("redirect_uri") and redirect_uri != pending["redirect_uri"]:
        raise HTTPException(400, "redirect_uri mismatch")

    challenge = pending.get("code_challenge", "")
    if challenge and not verify_pkce(
        challenge,
        pending.get("code_challenge_method", "S256"),
        code_verifier,
    ):
        raise HTTPException(400, "Invalid PKCE code_verifier")

    user = pending["user"]
    access_token = create_access_token(user, client_id=client_id or pending.get("client_id", ""))
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600 * 24 * 30,
        "scope": "openid email profile mcp",
    }


@router.get("/auth/me")
async def auth_me(request: Request):
    token = extract_bearer_token(request.headers.get("authorization"))
    user = verify_access_token(token) if token else None
    if not user:
        raise HTTPException(401, "Not authenticated")
    balance = get_balance(user["sub"]) if credits_enabled() else None
    return {
        "sub": user["sub"],
        "email": user.get("email"),
        "name": user.get("name"),
        "balance_usd": str(balance) if balance is not None else None,
        "credits_enabled": credits_enabled(),
    }


@router.post("/billing/checkout")
async def billing_checkout(request: Request):
    if not credits_enabled():
        raise HTTPException(503, "Stripe credits billing is not configured")
    token = extract_bearer_token(request.headers.get("authorization"))
    user = verify_access_token(token) if token else None
    if not user:
        raise HTTPException(401, "Sign in with Google OAuth first")
    session = create_checkout_session(google_sub=user["sub"], email=user.get("email", ""))
    return session


@router.post("/billing/webhook")
async def billing_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        result = handle_webhook(payload, sig)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return result


@router.get("/billing/success", response_class=HTMLResponse)
async def billing_success(session_id: str = ""):
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><title>Credits added</title></head>
<body style="font-family: system-ui; max-width: 32rem; margin: 4rem auto; padding: 0 1rem;">
  <h1>Credits added</h1>
  <p>Your ${10:.0f} AgentServices credit pack is on its way. Return to ChatGPT and retry your tool call.</p>
  {"<p><small>Session: " + session_id + "</small></p>" if session_id else ""}
</body></html>""")


@router.get("/billing/cancel", response_class=HTMLResponse)
async def billing_cancel():
    return HTMLResponse("""<!DOCTYPE html>
<html><head><title>Checkout canceled</title></head>
<body style="font-family: system-ui; max-width: 32rem; margin: 4rem auto; padding: 0 1rem;">
  <h1>Checkout canceled</h1>
  <p>No charge was made. You can buy credits anytime from the buy_credits MCP tool.</p>
</body></html>""")


def authenticate_mcp_request(request) -> dict[str, Any] | None:
    """Return verified user claims from MCP Authorization header, or None."""
    if not oauth_enabled():
        return None
    token = extract_bearer_token(request.headers.get("authorization"))
    if not token:
        return None
    return verify_access_token(token)
