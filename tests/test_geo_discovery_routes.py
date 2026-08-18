"""Discovery/GEO route contract tests for AgentServices."""
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from main import app  # noqa: E402

client = TestClient(app)


def test_well_known_llms_txt_matches_llms_txt():
    canonical = client.get("/llms.txt")
    well_known = client.get("/.well-known/llms.txt")

    assert canonical.status_code == 200
    assert well_known.status_code == 200
    assert canonical.headers["content-type"].startswith("text/plain")
    assert well_known.headers["content-type"].startswith("text/plain")
    assert canonical.text == well_known.text
    assert canonical.text.startswith("# AgentServices")


def test_server_json_serves_registry_manifest():
    response = client.get("/server.json")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "to.agentservices/agentservices"
    assert data["remotes"][0]["url"] == "https://agentservices.to/mcp"


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


def test_mcp_json_matches_well_known_mcp_json():
    root = client.get("/mcp.json")
    well_known = client.get("/.well-known/mcp.json")

    assert root.status_code == 200
    assert well_known.status_code == 200
    assert root.json() == well_known.json()
    assert root.json()["mcp_endpoint"] == "https://agentservices.to/mcp"


def test_server_json_matches_repo_file():
    repo_manifest = json.loads((ROOT / "server.json").read_text())
    response = client.get("/server.json")
    assert response.json() == repo_manifest
