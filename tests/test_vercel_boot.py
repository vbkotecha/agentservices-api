"""Ensure the FastAPI app can import on serverless-style environments."""
import importlib
import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def _fresh_import(module_name: str):
    sys.path.insert(0, str(SRC))
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


def test_agent_memory_uses_tmp_on_vercel():
    with patch.dict(os.environ, {"VERCEL": "1", "AGENTSERVICES_MEMORY_DIR": ""}, clear=False):
        agent_memory = _fresh_import("agent_memory")
        assert agent_memory._memory_dir().as_posix().startswith("/tmp/")


def test_index_exports_fastapi_app_with_health():
    for name in list(sys.modules):
        if name in ("main", "index") or name.startswith(("crypto_data", "agent_memory", "geo_data", "web_data")):
            sys.modules.pop(name, None)

    with patch.dict(os.environ, {"VERCEL": "1"}, clear=False):
        index_module = importlib.import_module("index")

    assert hasattr(index_module, "app")
    assert index_module.app.__class__.__name__ == "FastAPI"

    from fastapi.testclient import TestClient

    response = TestClient(index_module.app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_main_imports_on_vercel_without_root_writes():
    mkdir_targets: list[str] = []
    original_mkdir = Path.mkdir

    def tracking_mkdir(self, *args, **kwargs):
        mkdir_targets.append(self.as_posix())
        return original_mkdir(self, *args, **kwargs)

    for name in list(sys.modules):
        if name in ("main", "index") or name.startswith(("crypto_data", "agent_memory", "geo_data", "web_data")):
            sys.modules.pop(name, None)

    with patch.dict(os.environ, {"VERCEL": "1"}, clear=False), patch.object(Path, "mkdir", tracking_mkdir):
        index_module = importlib.import_module("index")

    assert hasattr(index_module, "app")
    assert not any(path.startswith("/root/") for path in mkdir_targets)


def test_letta_key_load_survives_permission_error_on_exists():
    """Vercel raises PermissionError on Path.exists() under /root/.letta."""
    original_exists = Path.exists

    def permission_exists(self):
        if self.as_posix().startswith("/root/.letta"):
            raise PermissionError(13, "Permission denied")
        return original_exists(self)

    modules_to_clear = [
        name
        for name in list(sys.modules)
        if name in ("main", "index", "letta_keys", "inference_gateway", "media_gateway", "pricing_cache", "voice_gateway")
        or name.startswith(("crypto_data", "agent_memory", "geo_data", "web_data"))
    ]
    for name in modules_to_clear:
        sys.modules.pop(name, None)

    env_without_keys = {
        key: ""
        for key in (
            "VERCEL",
            "OPENROUTER_API_KEY",
            "CODEXSALE_API_KEY",
            "CODEX_SALE_API_KEY",
            "GEMINI_API_KEY",
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN",
            "TWILIO_PHONE_NUMBER",
        )
    }
    env_without_keys["VERCEL"] = "1"

    with patch.dict(os.environ, env_without_keys, clear=False), patch.object(Path, "exists", permission_exists):
        letta_keys = _fresh_import("letta_keys")
        assert letta_keys.load_key("openrouter.key", "OPENROUTER_API_KEY") == ""
        assert letta_keys.load_json_key("twilio.json") == {}

        inference_gateway = _fresh_import("inference_gateway")
        assert inference_gateway.OPENROUTER_KEY == ""
        assert inference_gateway.CODEXSALE_KEY == ""
        assert inference_gateway.GEMINI_KEY == ""

        _fresh_import("media_gateway")
        _fresh_import("pricing_cache")
        _fresh_import("voice_gateway")

        index_module = importlib.import_module("index")
        assert hasattr(index_module, "app")

        from fastapi.testclient import TestClient

        response = TestClient(index_module.app).get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
