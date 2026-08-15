"""Vercel ASGI entrypoint.

Vercel zero-config FastAPI looks for ``app`` in ``index.py`` at the repo root.
We keep application code under ``src/`` and wire the path here so imports like
``from crypto_data import ...`` continue to work without a ``pyproject.toml``
(which would make Vercel prefer uv + incomplete lockfile installs).
"""
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from main import app  # noqa: F401
