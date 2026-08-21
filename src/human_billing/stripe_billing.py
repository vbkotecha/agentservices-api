"""Stripe Checkout + Customer Balance ledger for prepaid MCP credits."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
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

_MONEY_QUANT = Decimal("0.000001")


def _quantize(amount: Decimal) -> Decimal:
    return amount.quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP)


def _usd_to_cents(amount_usd: Decimal, *, debit: bool = False) -> int:
    cents = int((_quantize(amount_usd) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if debit and amount_usd > 0 and cents == 0:
        return 1
    return cents


def _stripe():
    import stripe

    stripe.api_key = stripe_secret_key()
    return stripe


def _credit_from_stripe_balance(balance_cents: int) -> Decimal:
    """Stripe negative customer balance = prepaid credit in USD."""
    return _quantize(Decimal(-balance_cents) / 100)


def find_or_create_customer(*, google_sub: str, email: str = "") -> dict[str, Any]:
    """Find or create a Stripe Customer keyed by Google sub."""
    stripe = _stripe()
    result = stripe.Customer.search(query=f'metadata["google_sub"]:"{google_sub}"', limit=1)
    customers = result.get("data") or []
    if customers:
        return customers[0]

    params: dict[str, Any] = {"metadata": {"google_sub": google_sub}}
    if email:
        params["email"] = email
    return stripe.Customer.create(**params)


def get_balance(google_sub: str) -> Decimal:
    customer = find_or_create_customer(google_sub=google_sub)
    balance_cents = customer.get("balance") or 0
    return _credit_from_stripe_balance(balance_cents)


def credit_balance(
    google_sub: str,
    amount_usd: Decimal,
    *,
    reference: str,
    source: str,
) -> Decimal:
    """Add prepaid credit via Stripe Customer Balance (negative balance = credit)."""
    amount_usd = _quantize(Decimal(str(amount_usd)))
    if amount_usd <= 0:
        raise ValueError("credit amount must be positive")

    stripe = _stripe()
    customer = find_or_create_customer(google_sub=google_sub)
    cents = _usd_to_cents(amount_usd)
    stripe.Customer.create_balance_transaction(
        customer["id"],
        amount=-cents,
        currency="usd",
        description=f"Credit: {source} ({reference})",
        metadata={"google_sub": google_sub, "reference": reference, "source": source},
        idempotency_key=f"credit-{reference}",
    )
    refreshed = stripe.Customer.retrieve(customer["id"])
    return _credit_from_stripe_balance(refreshed.get("balance") or 0)


def debit_balance(google_sub: str, amount_usd: Decimal, *, tool: str) -> Decimal:
    """Deduct prepaid credit for a successful paid MCP tool call."""
    amount_usd = _quantize(Decimal(str(amount_usd)))
    if amount_usd <= 0:
        raise ValueError("debit amount must be positive")

    balance = get_balance(google_sub)
    if balance < amount_usd:
        raise InsufficientCredits(balance, amount_usd)

    stripe = _stripe()
    customer = find_or_create_customer(google_sub=google_sub)
    cents = _usd_to_cents(amount_usd, debit=True)
    stripe.Customer.create_balance_transaction(
        customer["id"],
        amount=cents,
        currency="usd",
        description=f"MCP tool: {tool}",
        metadata={"google_sub": google_sub, "tool": tool},
    )
    refreshed = stripe.Customer.retrieve(customer["id"])
    return _credit_from_stripe_balance(refreshed.get("balance") or 0)


def has_sufficient_balance(google_sub: str, amount_usd: Decimal) -> bool:
    return get_balance(google_sub) >= _quantize(Decimal(str(amount_usd)))


class InsufficientCredits(Exception):
    def __init__(self, balance: Decimal, required: Decimal):
        self.balance = balance
        self.required = required
        super().__init__(f"Insufficient credits: have ${balance}, need ${required}")


def create_checkout_session(*, google_sub: str, email: str = "") -> dict[str, str]:
    if not credits_enabled():
        raise RuntimeError("Stripe credits billing is not configured")

    stripe = _stripe()
    customer = find_or_create_customer(google_sub=google_sub, email=email)
    base = public_base_url()
    metadata = {"google_sub": google_sub, "credits_usd": str(CREDITS_PACK_USD)}

    params: dict[str, Any] = {
        "mode": "payment",
        "customer": customer["id"],
        "success_url": f"{base}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{base}/billing/cancel",
        "client_reference_id": google_sub,
        "metadata": metadata,
    }
    if email and not customer.get("email"):
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
    if session.get("payment_status") != "paid":
        return {"status": "ignored", "reason": "payment_not_paid", "payment_status": session.get("payment_status")}

    google_sub = (session.get("metadata") or {}).get("google_sub") or session.get("client_reference_id")
    if not google_sub:
        return {"status": "error", "reason": "missing google_sub"}

    customer_id = session.get("customer")
    if customer_id:
        stripe.Customer.modify(customer_id, metadata={"google_sub": google_sub})
    else:
        find_or_create_customer(google_sub=google_sub, email=session.get("customer_details", {}).get("email", ""))

    amount_total = session.get("amount_total")
    if amount_total is not None:
        amount_usd = Decimal(amount_total) / 100
    else:
        amount_usd = Decimal(str(CREDITS_PACK_USD))

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
