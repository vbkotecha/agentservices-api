#!/usr/bin/env python3
"""Verify an end-to-end free AgentServices MCP tool call without credentials or payment.

Usage:
    python3 examples/mcp_free_tool_buyer_proof.py BTC,ETH

The script discovers the hosted Streamable HTTP MCP server, verifies the
`crypto_prices` tool is advertised as free, then invokes it through JSON-RPC.
It does not use a wallet, API key, session identifier, or paid tool.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

DISCOVERY_PROOF_PATH = Path(__file__).with_name("mcp_discovery_buyer_proof.py")
SPEC = importlib.util.spec_from_file_location("mcp_discovery_buyer_proof", DISCOVERY_PROOF_PATH)
assert SPEC and SPEC.loader
proof = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(proof)


def tool_by_name(tools: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for tool in tools:
        if tool.get("name") == name:
            return tool
    raise ValueError(f"MCP catalog does not advertise required tool: {name}")


def text_result(payload: dict[str, Any] | None) -> Any:
    result = proof.response_result(payload)
    content = result.get("content")
    if not isinstance(content, list) or not content:
        raise ValueError("MCP tools/call result contains no content")
    text = content[0].get("text") if isinstance(content[0], dict) else None
    if not isinstance(text, str):
        raise ValueError("MCP tools/call result has no text content")
    return json.loads(text)


def main() -> int:
    symbols = sys.argv[1] if len(sys.argv) > 1 else "BTC,ETH"
    discover_status, _, discover_payload = proof.post_jsonrpc(1, "server/discover", {})
    if discover_status != 200:
        print(f"MCP discovery failed: HTTP {discover_status}\n{discover_payload}", file=sys.stderr)
        return 1
    discovery = proof.response_result(discover_payload)
    if discovery.get("protocolVersion") != proof.PROTOCOL_VERSION:
        raise ValueError("hosted server did not return the expected MCP protocol version")

    tools_status, _, tools_payload = proof.post_jsonrpc(2, "tools/list", {})
    if tools_status != 200:
        print(f"MCP tools/list failed: HTTP {tools_status}\n{tools_payload}", file=sys.stderr)
        return 1
    tools = proof.response_result(tools_payload).get("tools")
    if not isinstance(tools, list):
        raise ValueError("MCP tools/list did not return a tool list")
    price_tool = tool_by_name(tools, "crypto_prices")
    if "FREE" not in price_tool.get("description", "").upper():
        raise ValueError("crypto_prices is not advertised as a free tool")

    call_status, _, call_payload = proof.post_jsonrpc(
        3,
        "tools/call",
        {"name": "crypto_prices", "arguments": {"symbols": symbols}},
    )
    if call_status != 200:
        print(f"MCP tools/call failed: HTTP {call_status}\n{call_payload}", file=sys.stderr)
        return 1
    result = text_result(call_payload)
    if not result:
        raise ValueError("crypto_prices returned an empty result")

    print(f"MCP FREE TOOL: HTTP 200 — crypto_prices({symbols})")
    print(json.dumps(result, indent=2, sort_keys=True))
    print("This proof validates a complete free MCP discovery and tool-call path; no wallet, API key, or paid tool was used.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
