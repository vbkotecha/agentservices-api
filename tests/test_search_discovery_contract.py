"""Keep Bazaar search discovery aligned with the live /v1/search response shape."""

import ast
import importlib
import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

MAIN_PATH = ROOT / "src" / "main.py"


def _discovery_entry() -> dict:
    tree = ast.parse(MAIN_PATH.read_text())
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == "_BAZAAR_ENDPOINT_INFO" for target in node.targets):
            entries = ast.literal_eval(node.value)
            return entries["/v1/search"]
    raise AssertionError("_BAZAAR_ENDPOINT_INFO was not found")


def test_search_discovery_example_is_object_matching_live_response():
    entry = _discovery_entry()
    example = entry["output_example"]

    assert isinstance(example, dict)
    assert entry["route"] == "/v1/search"
    assert entry["query"]["q"] == "bitcoin price"
    assert set(example) == {"query", "engine", "results", "count", "timestamp"}
    assert example["query"] == "bitcoin price"
    assert isinstance(example["results"], list)
    assert example["results"][0]["title"] == "Bitcoin Price"
    assert example["results"][0]["url"] == "https://example.com"
    assert example["results"][0]["snippet"] == "Current BTC price..."


def test_search_bazaar_extension_stamps_object_output_example():
    for name in list(sys.modules):
        if name in ("main", "index", "x402_payment") or name.startswith(
            ("crypto_data", "agent_memory", "geo_data", "web_data")
        ):
            sys.modules.pop(name, None)

    env = {
        "VERCEL": "1",
        "CDP_API_KEY_ID": "",
        "CDP_API_KEY_SECRET": "",
    }
    with patch.dict(os.environ, env, clear=False):
        main = importlib.import_module("main")

    bazaar_ext = main._build_bazaar_extension("/v1/search", "Web search")
    output = bazaar_ext["info"]["output"]
    assert output["type"] == "json"
    assert isinstance(output["example"], dict)
    assert isinstance(output["example"]["results"], list)

    schema_output = bazaar_ext["schema"]["properties"]["output"]
    assert schema_output["properties"]["example"]["type"] == "object"
