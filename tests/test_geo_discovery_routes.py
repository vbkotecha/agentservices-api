"""Discovery/GEO route contract tests for AgentServices."""
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from main import app  # noqa: E402

client = TestClient(app)

DISCOVERY_ENV = {
    "VERCEL": "1",
    "CDP_API_KEY_ID": "",
    "CDP_API_KEY_SECRET": "",
}


@pytest.fixture()
def discovery_client():
    modules = [
        name for name in list(sys.modules)
        if name in ("main", "index", "mcp_endpoint", "discovery_surfaces")
    ]
    for name in modules:
        sys.modules.pop(name, None)
    with patch.dict(os.environ, DISCOVERY_ENV, clear=False):
        from main import app as discovery_app
        yield TestClient(discovery_app)


def test_well_known_llms_txt_matches_llms_txt():
    canonical = client.get("/llms.txt")
    well_known = client.get("/.well-known/llms.txt")

    assert canonical.status_code == 200
    assert well_known.status_code == 200
    assert canonical.headers["content-type"].startswith("text/plain")
    assert well_known.headers["content-type"].startswith("text/plain")
    assert canonical.text == well_known.text
    assert canonical.text.startswith("# AgentServices")


def test_well_known_llms_full_txt_matches_llms_full_txt():
    canonical = client.get("/llms-full.txt")
    well_known = client.get("/.well-known/llms-full.txt")

    assert canonical.status_code == 200
    assert well_known.status_code == 200
    assert canonical.headers["content-type"].startswith("text/plain")
    assert well_known.headers["content-type"].startswith("text/plain")
    assert canonical.text == well_known.text
    assert canonical.text.startswith("# AgentServices")


def test_well_known_agents_txt_matches_agents_txt():
    canonical = client.get("/agents.txt")
    well_known = client.get("/.well-known/agents.txt")

    assert canonical.status_code == 200
    assert well_known.status_code == 200
    assert canonical.headers["content-type"].startswith("text/plain")
    assert well_known.headers["content-type"].startswith("text/plain")
    assert canonical.text == well_known.text
    assert canonical.text.startswith("# AgentServices")


def test_well_known_security_txt_matches_security_txt():
    canonical = client.get("/security.txt")
    well_known = client.get("/.well-known/security.txt")

    assert canonical.status_code == 200
    assert well_known.status_code == 200
    assert canonical.headers["content-type"].startswith("text/plain")
    assert well_known.headers["content-type"].startswith("text/plain")
    assert canonical.text == well_known.text
    assert "mailto:hustlemode@agentmail.to" in canonical.text
    assert "Canonical: https://agentservices.to/.well-known/security.txt" in canonical.text


def test_server_json_serves_registry_manifest():
    response = client.get("/server.json")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "to.agentservices/agentservices"
    assert data["remotes"][0]["url"] == "https://agentservices.to/mcp"


def test_well_known_server_json_matches_server_json():
    canonical = client.get("/server.json")
    well_known = client.get("/.well-known/server.json")

    assert canonical.status_code == 200
    assert well_known.status_code == 200
    assert canonical.headers["content-type"].startswith("application/json")
    assert well_known.headers["content-type"].startswith("application/json")
    assert canonical.json() == well_known.json()
    assert canonical.json()["name"] == "to.agentservices/agentservices"
    assert canonical.json()["remotes"][0]["url"] == "https://agentservices.to/mcp"


def test_well_known_openapi_json_matches_openapi_json():
    canonical = client.get("/openapi.json")
    well_known = client.get("/.well-known/openapi.json")

    assert canonical.status_code == 200
    assert well_known.status_code == 200
    assert canonical.headers["content-type"].startswith("application/json")
    assert well_known.headers["content-type"].startswith("application/json")
    assert canonical.json() == well_known.json()
    assert canonical.json()["info"]["title"] == "AgentServices"
    assert canonical.json()["info"]["version"] == well_known.json()["info"]["version"]


def test_well_known_schema_json_matches_schema_json():
    canonical = client.get("/schema.json")
    well_known = client.get("/.well-known/schema.json")

    assert canonical.status_code == 200
    assert well_known.status_code == 200
    assert canonical.headers["content-type"].startswith("application/json")
    assert well_known.headers["content-type"].startswith("application/json")
    assert canonical.json() == well_known.json()
    assert canonical.json()["info"]["title"] == "AgentServices"
    assert canonical.json()["info"]["version"] == well_known.json()["info"]["version"]


def test_schema_json_matches_openapi_json():
    schema = client.get("/schema.json")
    openapi = client.get("/openapi.json")

    assert schema.status_code == 200
    assert openapi.status_code == 200
    assert schema.json() == openapi.json()


def test_ai_plugin_json_matches_well_known_ai_plugin_json():
    canonical = client.get("/ai-plugin.json")
    well_known = client.get("/.well-known/ai-plugin.json")

    assert canonical.status_code == 200
    assert well_known.status_code == 200
    assert canonical.headers["content-type"].startswith("application/json")
    assert well_known.headers["content-type"].startswith("application/json")
    assert canonical.json() == well_known.json()
    assert canonical.json()["schema_version"] == "v1"
    assert canonical.json()["name_for_human"] == "AgentServices"


def test_mcp_json_matches_well_known_mcp_json():
    root = client.get("/mcp.json")
    well_known = client.get("/.well-known/mcp.json")

    assert root.status_code == 200
    assert well_known.status_code == 200
    assert root.json() == well_known.json()
    assert root.json()["mcp_endpoint"] == "https://agentservices.to/mcp"


def test_discovery_surfaces_mention_x402_rest(discovery_client):
    llms = discovery_client.get("/llms.txt")
    agents = discovery_client.get("/agents.txt")
    mcp = discovery_client.get("/mcp.json")
    plugin = discovery_client.get("/.well-known/ai-plugin.json")
    card = discovery_client.get("/.well-known/mcp/server-card.json")

    assert llms.status_code == 200
    assert agents.status_code == 200
    assert mcp.status_code == 200
    assert plugin.status_code == 200
    assert card.status_code == 200

    assert "x402" in llms.text
    assert "USDC on Base" in llms.text
    assert "x402" in agents.text
    assert mcp.json()["payment"]["rest"]["protocol"] == "x402"
    assert card.json()["pricing"]["rest"] == "Wallet agents pay via HTTP 402 on REST endpoints"


def test_discovery_no_longer_advertises_oauth_or_credit_billing(discovery_client):
    llms = discovery_client.get("/llms.txt")
    agents = discovery_client.get("/agents.txt")
    mcp = discovery_client.get("/mcp.json")
    plugin = discovery_client.get("/.well-known/ai-plugin.json")
    card = discovery_client.get("/.well-known/mcp/server-card.json")
    mcp_manifest = discovery_client.get("/.well-known/mcp")

    for response in (llms, agents, mcp, plugin, card, mcp_manifest):
        assert response.status_code == 200
        assert "Stripe" not in response.text
        assert "Google OAuth" not in response.text

    assert "https://agentservices.to/mcp" in llms.text
    assert "x402" in llms.text
    assert "x402-protected REST endpoints" in llms.text
    assert "Auth: None" in agents.text
    assert "Paid tools are refused through MCP" in agents.text

    mcp_data = mcp.json()
    assert mcp_data["mcp_endpoint"] == "https://agentservices.to/mcp"
    assert mcp_data["transport"] == "streamable-http"
    assert mcp_data["authentication"]["type"] == "none"
    assert mcp_data["payment"]["rest"]["protocol"] == "x402"
    assert "mcp_human" not in mcp_data["payment"]

    plugin_data = plugin.json()
    assert plugin_data["auth"]["type"] == "none"
    assert "x402" in plugin_data["description_for_human"]

    card_data = card.json()
    assert card_data["transport"]["endpoint"] == "https://agentservices.to/mcp"
    assert card_data["authentication"]["type"] == "none"
    assert "mcp_human" not in card_data["pricing"]

    assert mcp_manifest.json()["authentication"]["type"] == "none"


def test_server_json_matches_repo_file():
    repo_manifest = json.loads((ROOT / "server.json").read_text())
    response = client.get("/server.json")
    assert response.json() == repo_manifest
