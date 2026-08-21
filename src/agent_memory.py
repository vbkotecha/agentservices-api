"""
Agent Memory — Wallet-keyed persistent KV store with semantic recall.
Agents store state (context, preferences, history) on our server and retrieve it later.
This is a RETENTION HOOK — agents come back because their state lives here.

Endpoints:
- POST /v1/memory/{key} — Store a value ($0.01)
- GET /v1/memory/{key} — Retrieve a value ($0.01)
- GET /v1/memory — List all keys for caller's wallet ($0.01)
- DELETE /v1/memory/{key} — Delete a value ($0.01)
- POST /v1/memory/search — Semantic search across stored values ($0.02)
"""
import json
import os
import time
import hashlib
import re
from pathlib import Path

_MEMORY_DIR: Path | None = None


def _is_serverless() -> bool:
    """Detect Vercel/Lambda-style runtimes with read-only filesystems."""
    return any(
        os.environ.get(name)
        for name in ("VERCEL", "VERCEL_ENV", "AWS_LAMBDA_FUNCTION_NAME", "AWS_EXECUTION_ENV")
    )


def _default_memory_dir() -> Path:
    override = os.environ.get("AGENTSERVICES_MEMORY_DIR")
    if override:
        return Path(override)
    if _is_serverless():
        return Path("/tmp/agentservices-memory")
    return Path("/root/.letta/agent_memory")


def _memory_dir() -> Path:
    """Resolve a writable memory directory lazily (safe for Vercel cold starts)."""
    global _MEMORY_DIR
    if _MEMORY_DIR is not None:
        return _MEMORY_DIR

    for candidate in (_default_memory_dir(), Path("/tmp/agentservices-memory")):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            _MEMORY_DIR = candidate
            return _MEMORY_DIR
        except OSError:
            continue

    raise OSError("No writable directory available for agent memory")


def _wallet_dir(wallet: str) -> Path:
    """Get the memory directory for a specific wallet."""
    safe = hashlib.sha256(wallet.lower().encode()).hexdigest()[:16]
    d = _memory_dir() / safe
    d.mkdir(parents=True, exist_ok=True)
    return d


def store(wallet: str, key: str, value: str, ttl_seconds: int = 0):
    """Store a value for a wallet. TTL of 0 = permanent."""
    entry = {
        "key": key,
        "value": value,
        "wallet": wallet,
        "stored_at": time.time(),
        "ttl": ttl_seconds,
        "expires_at": time.time() + ttl_seconds if ttl_seconds > 0 else 0,
    }
    safe_key = re.sub(r'[^a-zA-Z0-9_\-]', '_', key)[:64]
    path = _wallet_dir(wallet) / f"{safe_key}.json"
    with open(path, 'w') as f:
        json.dump(entry, f)
    return {
        "status": "stored",
        "key": key,
        "wallet": wallet,
        "size_bytes": len(value),
        "ttl_seconds": ttl_seconds,
        "expires_at": entry["expires_at"] if ttl_seconds > 0 else None,
    }


def retrieve(wallet: str, key: str):
    """Retrieve a value for a wallet."""
    safe_key = re.sub(r'[^a-zA-Z0-9_\-]', '_', key)[:64]
    path = _wallet_dir(wallet) / f"{safe_key}.json"
    if not path.exists():
        return {"error": f"Key '{key}' not found", "status": "not_found"}
    with open(path) as f:
        entry = json.load(f)
    # Check TTL
    if entry.get("expires_at", 0) > 0 and time.time() > entry["expires_at"]:
        path.unlink()
        return {"error": f"Key '{key}' expired", "status": "expired"}
    return {
        "key": entry["key"],
        "value": entry["value"],
        "stored_at": entry["stored_at"],
        "age_seconds": int(time.time() - entry["stored_at"]),
    }


def list_keys(wallet: str):
    """List all keys for a wallet."""
    d = _wallet_dir(wallet)
    keys = []
    current_time = time.time()
    for path in d.glob("*.json"):
        try:
            with open(path) as f:
                entry = json.load(f)
            # Skip expired
            if entry.get("expires_at", 0) > 0 and current_time > entry["expires_at"]:
                continue
            keys.append({
                "key": entry["key"],
                "stored_at": entry["stored_at"],
                "size_bytes": len(entry.get("value", "")),
            })
        except:
            continue
    return {
        "wallet": wallet,
        "key_count": len(keys),
        "keys": keys,
    }


def delete(wallet: str, key: str):
    """Delete a value for a wallet."""
    safe_key = re.sub(r'[^a-zA-Z0-9_\-]', '_', key)[:64]
    path = _wallet_dir(wallet) / f"{safe_key}.json"
    if not path.exists():
        return {"error": f"Key '{key}' not found", "status": "not_found"}
    path.unlink()
    return {"status": "deleted", "key": key, "wallet": wallet}


def search(wallet: str, query: str, limit: int = 10):
    """
    Semantic search across all stored values for a wallet.
    Uses keyword overlap scoring (no LLM, no embeddings — pure Python).
    """
    d = _wallet_dir(wallet)
    query_words = set(re.findall(r'\b[a-zA-Z][a-zA-Z0-9]{2,}\b', query.lower()))
    if not query_words:
        return {"error": "Query too short or no keywords", "status": "error"}

    results = []
    current_time = time.time()

    for path in d.glob("*.json"):
        try:
            with open(path) as f:
                entry = json.load(f)
            # Skip expired
            if entry.get("expires_at", 0) > 0 and current_time > entry["expires_at"]:
                continue

            value = entry.get("value", "")
            key_name = entry.get("key", "")
            combined_text = (key_name + " " + value).lower()

            # Keyword overlap scoring
            value_words = set(re.findall(r'\b[a-zA-Z][a-zA-Z0-9]{2,}\b', combined_text))
            if not value_words:
                continue

            overlap = query_words & value_words
            score = len(overlap) / len(query_words)

            if score > 0:
                results.append({
                    "key": entry["key"],
                    "value_preview": value[:200],
                    "score": round(score, 2),
                    "matched_keywords": list(overlap)[:10],
                    "stored_at": entry["stored_at"],
                })
        except:
            continue

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)

    return {
        "wallet": wallet,
        "query": query,
        "results_count": len(results[:limit]),
        "results": results[:limit],
    }
