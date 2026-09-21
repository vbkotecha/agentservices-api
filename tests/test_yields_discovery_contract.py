"""Keep OpenAPI and Bazaar yields discovery aligned with get_defi_yields()."""

import ast
from pathlib import Path


MAIN_PATH = Path(__file__).resolve().parents[1] / "src" / "main.py"
CRYPTO_DATA_PATH = Path(__file__).resolve().parents[1] / "src" / "crypto_data.py"


def _discovery_entry() -> dict:
    tree = ast.parse(MAIN_PATH.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "_BAZAAR_ENDPOINT_INFO"
            for target in node.targets
        ):
            return ast.literal_eval(node.value)["/v1/yields"]
    raise AssertionError("_BAZAAR_ENDPOINT_INFO was not found")


def _open_api_yields_schema() -> dict:
    text = MAIN_PATH.read_text()
    marker = '@app.get("/v1/yields"'
    start = text.index(marker)
    schema_marker = '"schema":'
    schema_start = text.index(schema_marker, start) + len(schema_marker)
    depth = 0
    buf = []
    for ch in text[schema_start:]:
        if ch == "{":
            depth += 1
        if depth:
            buf.append(ch)
        if ch == "}":
            depth -= 1
            if depth == 0:
                break
    return ast.literal_eval("".join(buf))


def test_yields_discovery_example_matches_handler_envelope():
    example = _discovery_entry()["output_example"]

    assert set(example) == {"top_pools", "count", "timestamp"}
    assert example["count"] == len(example["top_pools"])
    assert isinstance(example["timestamp"], int)
    assert set(example["top_pools"][0]) == {
        "project", "chain", "symbol", "tvl_usd", "apy",
    }


def test_yields_openapi_requires_handler_owned_roots():
    schema = _open_api_yields_schema()

    assert schema["required"] == ["top_pools", "count", "timestamp"]
    item = schema["properties"]["top_pools"]["items"]
    assert item["required"] == ["project", "chain", "symbol", "tvl_usd", "apy"]


def test_yields_handler_source_still_returns_the_same_roots():
    source = CRYPTO_DATA_PATH.read_text()
    assert '"top_pools"' in source
    assert '"count"' in source
    assert '"timestamp"' in source
    assert '"project"' in source
    assert '"tvl_usd"' in source
