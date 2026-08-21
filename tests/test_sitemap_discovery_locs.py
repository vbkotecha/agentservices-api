"""Sitemap must list canonical discovery URLs for crawlers."""
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from main import app  # noqa: E402

client = TestClient(app)

REQUIRED_DISCOVERY_LOCS = [
    "https://agentservices.to/.well-known/llms.txt",
    "https://agentservices.to/.well-known/openapi.json",
    "https://agentservices.to/schema.json",
    "https://agentservices.to/.well-known/schema.json",
    "https://agentservices.to/server.json",
    "https://agentservices.to/mcp.json",
    "https://agentservices.to/agents.txt",
]


def test_sitemap_includes_discovery_locs():
    response = client.get("/sitemap.xml")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")

    body = response.text
    for loc in REQUIRED_DISCOVERY_LOCS:
        assert f"<loc>{loc}</loc>" in body, f"missing sitemap loc: {loc}"
