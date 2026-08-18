"""Configuration for the human billing door (Google OAuth + Stripe credits)."""
import os

DEFAULT_PUBLIC_BASE_URL = "https://agentservices.to"

CREDITS_PACK_USD = 10.0
CREDITS_PACK_CENTS = int(CREDITS_PACK_USD * 100)


def public_base_url() -> str:
    return (os.environ.get("PUBLIC_BASE_URL") or DEFAULT_PUBLIC_BASE_URL).rstrip("/")


def google_client_id() -> str:
    return os.environ.get("GOOGLE_CLIENT_ID", "")


def google_client_secret() -> str:
    return os.environ.get("GOOGLE_CLIENT_SECRET", "")


def stripe_secret_key() -> str:
    return os.environ.get("STRIPE_SECRET_KEY", "")


def stripe_webhook_secret() -> str:
    return os.environ.get("STRIPE_WEBHOOK_SECRET", "")


def stripe_price_credits_10() -> str:
    return os.environ.get("STRIPE_PRICE_CREDITS_10", "")


def oauth_jwt_secret() -> str:
    return os.environ.get("OAUTH_JWT_SECRET") or os.environ.get("SESSION_SECRET") or ""


def credits_storage_dir() -> str:
    return os.environ.get("AGENTSERVICES_CREDITS_DIR", "")


def oauth_enabled() -> bool:
    return bool(google_client_id() and google_client_secret() and oauth_jwt_secret())


def credits_enabled() -> bool:
    return bool(stripe_secret_key() and oauth_enabled())


def human_door_enabled() -> bool:
    return oauth_enabled()
