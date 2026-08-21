"""Offline regression checks for the Streamable HTTP MCP buyer proof."""

import importlib.util
from pathlib import Path


EXAMPLE_PATH = Path(__file__).resolve().parents[1] / "examples" / "mcp_discovery_buyer_proof.py"
SPEC = importlib.util.spec_from_file_location("mcp_discovery_buyer_proof", EXAMPLE_PATH)
assert SPEC and SPEC.loader
proof = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(proof)


def test_response_result_accepts_jsonrpc_result_object():
    assert proof.response_result({"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}) == {"tools": []}


def test_response_result_rejects_jsonrpc_errors():
    try:
        proof.response_result({"jsonrpc": "2.0", "id": 1, "error": {"code": -32601}})
    except ValueError as error:
        assert "JSON-RPC error" in str(error)
    else:
        raise AssertionError("JSON-RPC error payload should raise ValueError")
