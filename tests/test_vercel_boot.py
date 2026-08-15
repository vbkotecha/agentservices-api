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


def test_main_imports_on_vercel_without_root_writes():
    mkdir_targets: list[str] = []
    original_mkdir = Path.mkdir

    def tracking_mkdir(self, *args, **kwargs):
        mkdir_targets.append(self.as_posix())
        return original_mkdir(self, *args, **kwargs)

    for name in list(sys.modules):
        if name == "main" or name.startswith(("crypto_data", "agent_memory", "geo_data", "web_data")):
            sys.modules.pop(name, None)

    with patch.dict(os.environ, {"VERCEL": "1"}, clear=False), patch.object(Path, "mkdir", tracking_mkdir):
        app_module = _fresh_import("main")

    assert hasattr(app_module, "app")
    assert not any(path.startswith("/root/") for path in mkdir_targets)
