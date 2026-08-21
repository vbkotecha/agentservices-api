"""
Dynamic pricing cache for inference gateway.
Fetches per-token rates from OpenRouter, calculates provider-cost-plus-margin pricing.

Matches BlockRun's model: provider cost + 5%, floor $0.003.
"""
import urllib.request
import json
import time

from letta_keys import load_key

OPENROUTER_KEY = load_key("openrouter.key", "OPENROUTER_API_KEY")
OPENROUTER_BASE = "https://openrouter.ai/api/v1"

# Cache: model_id -> {"prompt": float, "completion": float}
_pricing_cache = {}
_last_fetch = 0
_CACHE_TTL = 3600  # 1 hour

MARGIN = 1.05  # 5% margin
FLOOR = 0.003  # $0.003 minimum per call (matches BlockRun)

# Curated model price overrides for direct APIs (Gemini free tier = 0 cost)
DIRECT_PROVIDERS = {
    "gemini-2.0-flash": {"prompt": 0.0, "completion": 0.0},
    "gemini-2.5-flash": {"prompt": 0.0, "completion": 0.0},
    "gemini-2.5-pro": {"prompt": 0.0, "completion": 0.0},
}


def fetch_pricing():
    """Fetch and cache all model pricing from OpenRouter."""
    global _last_fetch, _pricing_cache
    try:
        headers = {"Authorization": f"Bearer {OPENROUTER_KEY}"} if OPENROUTER_KEY else {}
        req = urllib.request.Request(
            f"{OPENROUTER_BASE}/models",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        models = data.get("data", [])
        for m in models:
            mid = m.get("id", "")
            pricing = m.get("pricing", {})
            prompt_cost = float(pricing.get("prompt", "0") or "0")
            completion_cost = float(pricing.get("completion", "0") or "0")
            _pricing_cache[mid] = {"prompt": prompt_cost, "completion": completion_cost}
        _last_fetch = time.time()
        print(f"[pricing] Cached {len(_pricing_cache)} model prices from OpenRouter", flush=True)
    except Exception as e:
        print(f"[pricing] Failed to fetch: {e}", flush=True)


def get_model_pricing(model_id: str) -> dict:
    """Get per-token pricing for a model. Returns {"prompt": float, "completion": float}."""
    # Refresh cache if stale
    if time.time() - _last_fetch > _CACHE_TTL:
        fetch_pricing()

    # Check cache
    if model_id in _pricing_cache:
        return _pricing_cache[model_id]

    # Check direct providers (Gemini free tier)
    if model_id in DIRECT_PROVIDERS:
        return DIRECT_PROVIDERS[model_id]

    # Unknown models use a conservative premium estimate. Never undercharge.
    return {"prompt": 0.00001, "completion": 0.00005}


def estimate_input_tokens(messages: list) -> int:
    """Estimate input token count from messages. ~4 chars per token."""
    total_chars = sum(len(str(m.get("content", ""))) for m in messages)
    # Add overhead for role tags and formatting
    return int(total_chars / 4) + len(messages) * 4


def calculate_price(model_id: str, messages: list, max_tokens: int = 1000) -> str:
    """
    Calculate dynamic price for a chat completion request.
    Returns a price string like "$0.008" suitable for x402.

    Formula: (estimated_input_tokens * prompt_per_token + max_tokens * completion_per_token) * MARGIN
    Floor: $0.003
    """
    pricing = get_model_pricing(model_id)
    input_tokens = estimate_input_tokens(messages)

    cost = (input_tokens * pricing["prompt"] + max_tokens * pricing["completion"]) * MARGIN

    # Apply floor
    if cost < FLOOR:
        cost = FLOOR

    # Round up to 3 decimal places
    import math
    cost = math.ceil(cost * 1000) / 1000

    return f"${cost:.3f}"


def pricing_summary():
    """Return a summary of cached pricing data."""
    return {
        "models_cached": len(_pricing_cache),
        "cache_age_seconds": int(time.time() - _last_fetch) if _last_fetch else None,
        "margin": f"+{int((MARGIN - 1) * 100)}%",
        "floor": f"${FLOOR}",
        "note": "Dynamic pricing: provider cost + 5%, floor $0.003. Price calculated per request from model, input size, and max_tokens.",
    }
