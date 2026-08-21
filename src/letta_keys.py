"""Safe API key loading for local/Railway (/root/.letta) and serverless (Vercel).

On Vercel, Path.exists() on /root/.letta paths can raise PermissionError instead
of returning False. All key reads go through helpers here so import-time module
loads never crash on unreadable paths.
"""
import json
import os
from pathlib import Path

LETTA_KEYS_DIR = Path("/root/.letta/keys")


def _safe_path_exists(path: Path) -> bool:
    try:
        return path.exists()
    except (PermissionError, OSError):
        return False


def _safe_read_text(path: Path) -> str:
    try:
        if not _safe_path_exists(path):
            return ""
        return path.read_text(encoding="utf-8").strip()
    except (PermissionError, OSError):
        return ""


def load_key(filename: str, *env_vars: str) -> str:
    """Load a secret: prefer env vars, then /root/.letta/keys/<filename>."""
    for name in env_vars:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return _safe_read_text(LETTA_KEYS_DIR / filename)


def load_json_key(filename: str) -> dict:
    text = _safe_read_text(LETTA_KEYS_DIR / filename)
    if not text:
        return {}
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def load_twilio_config() -> dict:
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
    token = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    phone = os.environ.get("TWILIO_PHONE_NUMBER", "").strip()
    if sid and token:
        return {"account_sid": sid, "auth_token": token, "phone_number": phone}
    return load_json_key("twilio.json")
