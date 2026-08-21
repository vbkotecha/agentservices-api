#!/usr/bin/env python3
"""Verify AgentServices Streamable HTTP MCP discovery without credentials or payment.

Usage:
    python3 examples/mcp_discovery_buyer_proof.py

The script proves that an MCP-compatible buyer can discover the hosted server
and its tool catalog through JSON-RPC. It does not invoke paid tools, use a
wallet, or require a session identifier.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any

MCP_URL = "https://agentservices.to/mcp"
PROTOCOL_VERSION = "2026-07-28"
EXPECTED_FREE_TOOLS = {"crypto_prices", "fear_greed", "agent_context"}


def post_jsonrpc(request_id: int, method: str, params: dict[str, Any]) -> tuple[int, dict[str, str], dict[str, Any] | None]:
    """POST one MCP JSON-RPC request using Streamable HTTP discovery headers."""
    request = urllib.request.Request(
        MCP_URL,
        data=json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Mcp-Method": method,
            "Mcp-Name": "agentservices",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            return response.status, dict(response.headers.items()), json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        payload = json.loads(body) if body else None
        return error.code, dict(error.headers.items()), payload


def response_result(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        raise ValueError("MCP server returned an empty JSON-RPC response")
    if "error" in payload:
        raise ValueError(f"MCP JSON-RPC error: {payload['error']}")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise ValueError(f"MCP response is missing an object result: {payload}")
    return result


def main() -> int:
    discover_status, _, discover_payload = post_jsonrpc(1, "server/discover", {})
    if discover_status != 200:
        print(f"MCP discovery failed: HTTP {discover_status}\n{discover_payload}", file=sys.stderr)
        return 1
    discovery = response_result(discover_payload)
    if discovery.get("protocolVersion") != PROTOCOL_VERSION:
        raise ValueError(f"expected MCP protocol {PROTOCOL_VERSION}, got {discovery.get('protocolVersion')}")

    server_info = discovery.get("serverInfo") or {}
    print(f"MCP DISCOVERY: HTTP 200 — {server_info.get('name')} v{server_info.get('version')}")
    print(f"protocol: {discovery['protocolVersion']}")

    tools_status, tools_headers, tools_payload = post_jsonrpc(2, "tools/list", {})
    if tools_status != 200:
        print(f"MCP tools/list failed: HTTP {tools_status}\n{tools_payload}", file=sys.stderr)
        return 1
    tools_result = response_result(tools_payload)
    tools = tools_result.get("tools")
    if not isinstance(tools, list) or not tools:
        raise ValueError("MCP tools/list did not return a non-empty tool catalog")

    names = {tool.get("name") for tool in tools if tool.get("name")}
    missing = EXPECTED_FREE_TOOLS - names
    if missing:
        raise ValueError(f"expected free MCP tools missing from catalog: {sorted(missing)}")

    print(f"MCP TOOLS: HTTP 200 — {len(tools)} tools discovered")
    print(f"cache-control: {next((value for key, value in tools_headers.items() if key.lower() == 'cache-control'), 'not supplied')}")
    print(f"verified free tools: {', '.join(sorted(EXPECTED_FREE_TOOLS))}")
    print("This proof validates MCP server discovery only; no paid tool was invoked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
