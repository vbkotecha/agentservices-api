"""Stripe Checkout + webhook handler for prepaid credit packs."""
from typing import Any

from human_billing.config import (
    CREDITS_PACK_CENTS,
    CREDITS_PACK_USD,
    credits_enabled,
    public_base_url,
    stripe_price_credits_10,
    stripe_secret_key,
    stripe_webhook_secret,
)
from human_billing.credits import credit_balance


def _stripe():
    import stripe

    stripe.api_key = stripe_secret_key()
    return stripe


def create_checkout_session(*, google_sub: str, email: str = "") -> dict[str, str]:
    if not credits_enabled():
        raise RuntimeError("Stripe credits billing is not configured")

    stripe = _stripe()
    base = public_base_url()
    metadata = {"google_sub": google_sub, "credits_usd": str(CREDITS_PACK_USD)}

    params: dict[str, Any] = {
        "mode": "payment",
        "success_url": f"{base}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{base}/billing/cancel",
        "client_reference_id": google_sub,
        "metadata": metadata,
    }
    if email:
        params["customer_email"] = email

    price_id = stripe_price_credits_10()
    if price_id:
        params["line_items"] = [{"price": price_id, "quantity": 1}]
    else:
        params["line_items"] = [{
            "price_data": {
                "currency": "usd",
                "unit_amount": CREDITS_PACK_CENTS,
                "product_data": {
                    "name": "AgentServices Credits",
                    "description": f"${CREDITS_PACK_USD:.0f} prepaid API credits for MCP tools",
                },
            },
            "quantity": 1,
        }]

    session = stripe.checkout.Session.create(**params)
    return {"checkout_url": session.url, "session_id": session.id}


def handle_webhook(payload: bytes, sig_header: str) -> dict[str, Any]:
    if not credits_enabled():
        return {"status": "ignored", "reason": "credits_disabled"}

    stripe = _stripe()
    secret = stripe_webhook_secret()
    if not secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET is not configured")

    event = stripe.Webhook.construct_event(payload, sig_header, secret)

    if event["type"] != "checkout.session.completed":
        return {"status": "ignored", "type": event["type"]}

    session = event["data"]["object"]
    google_sub = (session.get("metadata") or {}).get("google_sub") or session.get("client_reference_id")
    if not google_sub:
        return {"status": "error", "reason": "missing google_sub"}

    amount_total = session.get("amount_total")
    if amount_total is not None:
        amount_usd = amount_total / 100
    else:
        amount_usd = CREDITS_PACK_USD

    balance = credit_balance(
        google_sub,
        amount_usd,
        reference=session["id"],
        source="stripe_checkout",
    )
    return {
        "status": "credited",
        "google_sub": google_sub,
        "amount_usd": str(amount_usd),
        "balance_usd": str(balance),
        "session_id": session["id"],
    }
