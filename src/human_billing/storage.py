"""Durable key-value storage for credits and OAuth pending state.

Production: Redis via REDIS_URL (Upstash-compatible).
Local/tests: file backend when REDIS_URL is unset (or AGENTSERVICES_CREDITS_DIR override).
"""
from __future__ import annotations

import json
import os
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from human_billing.config import credits_storage_dir, redis_url

_LOCK = threading.Lock()
_STORE: "KVStore | None" = None

OAUTH_PENDING_TTL_SECONDS = 600


class KVStore(ABC):
    @abstractmethod
    def get(self, key: str) -> str | None: ...

    @abstractmethod
    def set(self, key: str, value: str, *, ttl_seconds: int | None = None) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> bool: ...

    def get_json(self, key: str) -> dict | None:
        raw = self.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    def set_json(self, key: str, value: dict, *, ttl_seconds: int | None = None) -> None:
        self.set(key, json.dumps(value), ttl_seconds=ttl_seconds)

    def pop_json(self, key: str) -> dict | None:
        with _LOCK:
            data = self.get_json(key)
            if data is not None:
                self.delete(key)
            return data


class FileKVStore(KVStore):
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = key.replace("/", "__")
        return self.root / f"{safe}.json"

    def get(self, key: str) -> str | None:
        path = self._path(key)
        if not path.exists():
            return None
        with open(path) as f:
            envelope = json.load(f)
        expires_at = envelope.get("expires_at")
        if expires_at and time.time() > expires_at:
            path.unlink(missing_ok=True)
            return None
        return envelope.get("value")

    def set(self, key: str, value: str, *, ttl_seconds: int | None = None) -> None:
        envelope: dict[str, Any] = {"value": value}
        if ttl_seconds:
            envelope["expires_at"] = time.time() + ttl_seconds
        with open(self._path(key), "w") as f:
            json.dump(envelope, f)

    def delete(self, key: str) -> bool:
        path = self._path(key)
        if path.exists():
            path.unlink()
            return True
        return False


class RedisKVStore(KVStore):
    def __init__(self, url: str):
        import redis

        self.client = redis.from_url(url, decode_responses=True)

    def get(self, key: str) -> str | None:
        return self.client.get(key)

    def set(self, key: str, value: str, *, ttl_seconds: int | None = None) -> None:
        if ttl_seconds:
            self.client.setex(key, ttl_seconds, value)
        else:
            self.client.set(key, value)

    def delete(self, key: str) -> bool:
        return bool(self.client.delete(key))


def _is_serverless() -> bool:
    return any(
        os.environ.get(name)
        for name in ("VERCEL", "VERCEL_ENV", "AWS_LAMBDA_FUNCTION_NAME", "AWS_EXECUTION_ENV")
    )


def _default_file_root() -> Path:
    override = credits_storage_dir()
    if override:
        return Path(override)
    return Path("/tmp/agentservices-kv")


def durable_storage_available() -> bool:
    if redis_url():
        return True
    if credits_storage_dir():
        return True
    return not _is_serverless()


def get_store() -> KVStore:
    global _STORE
    if _STORE is not None:
        return _STORE

    url = redis_url()
    if url:
        _STORE = RedisKVStore(url)
        return _STORE

    if credits_storage_dir() or not _is_serverless():
        _STORE = FileKVStore(_default_file_root())
        return _STORE

    raise RuntimeError(
        "REDIS_URL is required for durable storage on Vercel. "
        "Set REDIS_URL to an Upstash-compatible Redis URL."
    )


def reset_store_for_tests(store: KVStore | None = None) -> None:
    """Reset cached store (tests only)."""
    global _STORE
    _STORE = store
