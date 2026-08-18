"""Prepaid credit ledger backed by durable KV storage (Redis or local file)."""
import hashlib
import re
import threading
import time
from decimal import Decimal, ROUND_HALF_UP

from human_billing.storage import get_store

_LOCK = threading.Lock()
_MONEY_QUANT = Decimal("0.000001")

ACCOUNT_PREFIX = "credits:account:"
WEBHOOK_PREFIX = "credits:webhook:"


def _user_key(google_sub: str) -> str:
    safe = hashlib.sha256(google_sub.encode()).hexdigest()[:32]
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", safe)


def _account_key(google_sub: str) -> str:
    return f"{ACCOUNT_PREFIX}{_user_key(google_sub)}"


def _quantize(amount: Decimal) -> Decimal:
    return amount.quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP)


def _load_account(google_sub: str) -> dict:
    store = get_store()
    account = store.get_json(_account_key(google_sub))
    if not account:
        return {
            "google_sub": google_sub,
            "balance_usd": "0",
            "updated_at": time.time(),
            "transactions": [],
        }
    return account


def _save_account(account: dict) -> None:
    account["updated_at"] = time.time()
    get_store().set_json(_account_key(account["google_sub"]), account)


def get_balance(google_sub: str) -> Decimal:
    with _LOCK:
        account = _load_account(google_sub)
        return _quantize(Decimal(account.get("balance_usd", "0")))


def credit_balance(google_sub: str, amount_usd: Decimal, *, reference: str, source: str) -> Decimal:
    """Add credits idempotently when reference is a Stripe session id."""
    amount_usd = _quantize(Decimal(str(amount_usd)))
    if amount_usd <= 0:
        raise ValueError("credit amount must be positive")

    with _LOCK:
        store = get_store()
        webhook_key = f"{WEBHOOK_PREFIX}{reference}"
        if store.get(webhook_key):
            return _quantize(Decimal(_load_account(google_sub).get("balance_usd", "0")))

        account = _load_account(google_sub)
        balance = _quantize(Decimal(account.get("balance_usd", "0")) + amount_usd)
        account["balance_usd"] = str(balance)
        account.setdefault("transactions", []).append({
            "type": "credit",
            "amount_usd": str(amount_usd),
            "reference": reference,
            "source": source,
            "at": time.time(),
        })
        _save_account(account)
        store.set_json(webhook_key, {
            "google_sub": google_sub,
            "amount_usd": str(amount_usd),
            "at": time.time(),
        })
        return balance


def debit_balance(google_sub: str, amount_usd: Decimal, *, tool: str) -> Decimal:
    """Deduct credits for a successful paid MCP tool call."""
    amount_usd = _quantize(Decimal(str(amount_usd)))
    if amount_usd <= 0:
        raise ValueError("debit amount must be positive")

    with _LOCK:
        account = _load_account(google_sub)
        balance = _quantize(Decimal(account.get("balance_usd", "0")))
        if balance < amount_usd:
            raise InsufficientCredits(balance, amount_usd)

        balance = _quantize(balance - amount_usd)
        account["balance_usd"] = str(balance)
        account.setdefault("transactions", []).append({
            "type": "debit",
            "amount_usd": str(amount_usd),
            "tool": tool,
            "at": time.time(),
        })
        _save_account(account)
        return balance


def has_sufficient_balance(google_sub: str, amount_usd: Decimal) -> bool:
    balance = get_balance(google_sub)
    return balance >= _quantize(Decimal(str(amount_usd)))


class InsufficientCredits(Exception):
    def __init__(self, balance: Decimal, required: Decimal):
        self.balance = balance
        self.required = required
        super().__init__(f"Insufficient credits: have ${balance}, need ${required}")
