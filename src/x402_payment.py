"""
x402 Payment Protocol integration for AgentCourt.
Uses Coinbase Developer Platform (CDP) as the facilitator for Base Mainnet.
Lightweight JWT generation — no cdp-sdk dependency needed.
"""
import base64
import json
import random
import time

from cryptography.hazmat.primitives.asymmetric import ed25519

from letta_keys import load_key

CDP_API_KEY = load_key("cdp_api_key_id.key", "CDP_API_KEY_ID")
CDP_API_SECRET = load_key("cdp_api_key_secret.key", "CDP_API_KEY_SECRET")
CDP_FACILITATOR_URL = "https://api.cdp.coinbase.com/platform/v2/x402"


def cdp_auth_available() -> bool:
    """True when CDP JWT credentials are configured for facilitator verify/settle."""
    return bool(CDP_API_KEY and CDP_API_SECRET)


def base_supported_response():
    """Static facilitator capabilities for Base mainnet when CDP auth is unavailable."""
    from x402.schemas.responses import SupportedKind, SupportedResponse

    return SupportedResponse(
        kinds=[SupportedKind(x402_version=2, scheme="exact", network="eip155:8453")],
    )


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def _load_ed25519_key(secret_b64: str):
    """Load Ed25519 private key from base64-encoded key material."""
    raw = base64.b64decode(secret_b64)
    if len(raw) == 64:
        seed = raw[:32]
    elif len(raw) == 32:
        seed = raw
    else:
        raise ValueError(f"Invalid key length: {len(raw)} bytes")
    return ed25519.Ed25519PrivateKey.from_private_bytes(seed)


def _generate_jwt(method: str, host: str, path: str) -> str:
    """Generate a CDP-compatible JWT signed with Ed25519."""
    if not cdp_auth_available():
        raise ValueError("CDP_API_KEY_ID and CDP_API_KEY_SECRET must be set")

    private_key = _load_ed25519_key(CDP_API_SECRET)

    now = int(time.time())
    nonce = str(random.randint(0, 2**53))

    header = {"alg": "EdDSA", "kid": CDP_API_KEY, "nonce": nonce, "typ": "JWT"}
    payload = {
        "sub": CDP_API_KEY,
        "iss": "cdp",
        "aud": None,
        "nbf": now,
        "exp": now + 120,
        "uris": [f"{method} {host}{path}"],
    }

    header_b64 = _b64url_encode(json.dumps(header, separators=(',', ':')).encode())
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(',', ':'), sort_keys=True).encode())

    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = private_key.sign(signing_input)
    sig_b64 = _b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def create_cdp_auth_headers():
    """Generate CDP JWT auth headers for each x402 facilitator endpoint."""
    if not cdp_auth_available():
        raise ValueError("CDP_API_KEY_ID and CDP_API_KEY_SECRET must be set")

    headers = {}
    for method, path, key in [
        ("POST", "/verify", "verify"),
        ("POST", "/settle", "settle"),
        ("GET", "/supported", "supported"),
    ]:
        full_path = f"/platform/v2/x402{path}"
        token = _generate_jwt(method, "api.cdp.coinbase.com", full_path)
        headers[key] = {"Authorization": f"Bearer {token}"}

    return headers
