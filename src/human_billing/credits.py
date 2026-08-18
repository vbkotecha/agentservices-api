"""Prepaid credit ledger — file-backed, one balance per Google user."""
import hashlib
import json
import os
import re
import threading
import time
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from human_billing.config import credits_storage_dir

_CREDITS_DIR: Path | None = None
_LOCK = threading.Lock()
_MONEY_QUANT = Decimal("0.000001")


def _is_serverless() -> bool:
    return any(
        os.environ.get(name)
        for name in ("VERCEL", "VERCEL_ENV", "AWS_LAMBDA_FUNCTION_NAME", "AWS_EXECUTION_ENV")
    )


def _default_credits_dir() -> Path:
    override = credits_storage_dir()
    if override:
        return Path(override)
    if _is_serverless():
        return Path("/tmp/agentservices-credits")
    return Path("/tmp/agentservices-credits")


def _credits_dir() -> Path:
    global _CREDITS_DIR
    if _CREDITS_DIR is not None:
        return _CREDITS_DIR

    for candidate in (_default_credits_dir(), Path("/tmp/agentservices-credits")):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            _CREDITS_DIR = candidate
            return _CREDITS_DIR
        except OSError:
            continue

    raise OSError("No writable directory available for credit storage")


def _user_key(google_sub: str) -> str:
    safe = hashlib.sha256(google_sub.encode()).hexdigest()[:32]
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", safe)


def _balance_path(google_sub: str) -> Path:
    return _credits_dir() / f"{_user_key(google_sub)}.json"


def _webhook_path() -> Path:
    return _credits_dir() / "_stripe_sessions.json"


def _quantize(amount: Decimal) -> Decimal:
    return amount.quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP)


def _load_account(google_sub: str) -> dict:
    path = _balance_path(google_sub)
    if not path.exists():
        return {
            "google_sub": google_sub,
            "balance_usd": "0",
            "updated_at": time.time(),
            "transactions": [],
        }
    with open(path) as f:
        return json.load(f)


def _save_account(account: dict) -> None:
    account["updated_at"] = time.time()
    path = _balance_path(account["google_sub"])
    with open(path, "w") as f:
        json.dump(account, f)


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
        if _webhook_already_processed(reference):
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
        _mark_webhook_processed(reference, google_sub, str(amount_usd))
        return balance


def debit_balance(google_sub: str, amount_usd: Decimal, *, tool: str) -> Decimal:
    """Deduct credits for a paid MCP tool call. Raises InsufficientCredits if too low."""
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


class InsufficientCredits(Exception):
    def __init__(self, balance: Decimal, required: Decimal):
        self.balance = balance
        self.required = required
        super().__init__(f"Insufficient credits: have ${balance}, need ${required}")


def _webhook_already_processed(session_id: str) -> bool:
    path = _webhook_path()
    if not path.exists():
        return False
    with open(path) as f:
        data = json.load(f)
    return session_id in data.get("processed", {})


def _mark_webhook_processed(session_id: str, google_sub: str, amount_usd: str) -> None:
    path = _webhook_path()
    data = {"processed": {}}
    if path.exists():
        with open(path) as f:
            data = json.load(f)
    data.setdefault("processed", {})[session_id] = {
        "google_sub": google_sub,
        "amount_usd": amount_usd,
        "at": time.time(),
    }
    with open(path, "w") as f:
        json.dump(data, f)
