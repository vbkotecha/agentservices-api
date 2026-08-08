"""Offline regression checks for the free MCP tool buyer proof."""
import importlib.util
from pathlib import Path

EXAMPLE_PATH = Path(__file__).resolve().parents[1] / "examples" / "mcp_free_tool_buyer_proof.py"
SPEC = importlib.util.spec_from_file_location("mcp_free_tool_buyer_proof", EXAMPLE_PATH)
assert SPEC and SPEC.loader
proof = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(proof)


def test_tool_by_name_returns_advertised_tool():
    tool = {"name": "crypto_prices", "description": "Current crypto prices (FREE)"}
    assert proof.tool_by_name([tool], "crypto_prices") == tool


def test_text_result_decodes_jsonrpc_text_content():
    payload = {"jsonrpc": "2.0", "id": 3, "result": {"content": [{"type": "text", "text": '{"BTC": 1}'}]}}
    assert proof.text_result(payload) == {"BTC": 1}
