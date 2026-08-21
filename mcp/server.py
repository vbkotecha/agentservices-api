"""
AgentServices MCP Server — Exposes x402 data APIs as MCP tools.
AI agents can discover and call AgentServices endpoints through Model Context Protocol.
"""
import json
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

SERVER = Server("agentservices")
BASE_URL = "https://agentservices.to"

ENDPOINTS = {
    "crypto_prices": {
        "path": "/v1/crypto/prices",
        "method": "GET",
        "description": "Get current crypto prices (FREE)",
        "params": {"symbols": "Comma-separated crypto symbols (e.g., BTC,ETH,XRP)"}
    },
    "technical_indicators": {
        "path": "/v1/indicators",
        "method": "GET",
        "description": "Get technical indicators (RSI, MACD, etc.) — $0.02 via x402",
        "params": {"symbol": "Crypto symbol", "interval": "1h|4h|1d"}
    },
    "defi_yields": {
        "path": "/v1/defi/yields",
        "method": "GET",
        "description": "Get DeFi yield rates across protocols — $0.02 via x402",
        "params": {"chain": "Blockchain name", "protocol": "Protocol name (optional)"}
    },
    "fear_greed": {
        "path": "/v1/fear-greed",
        "method": "GET",
        "description": "Get crypto Fear & Greed index (FREE)",
        "params": {}
    },
    "ip_geolocation": {
        "path": "/v1/geo",
        "method": "GET",
        "description": "Get IP geolocation data (FREE)",
        "params": {"ip": "IP address"}
    },
    "url_metadata": {
        "path": "/v1/metadata",
        "method": "GET",
        "description": "Extract metadata from any URL — $0.01 via x402",
        "params": {"url": "URL to extract metadata from"}
    },
    "resolve_dispute": {
        "path": "/v1/disputes",
        "method": "POST",
        "description": "AI-powered dispute resolution (AgentCourt engine) — $0.05 via x402",
        "params": {
            "policy": "Policy ID (mileage_payment, physical_commerce, freelance_delivery, bug_bounty, api_quality, sla_monitoring, scope_dispute)",
            "dispute": "Dispute details as JSON object"
        }
    },
    "list_policies": {
        "path": "/v1/policies",
        "method": "GET",
        "description": "List all available dispute resolution policies (FREE)",
        "params": {}
    }
}

@SERVER.list_tools()
async def list_tools() -> list[Tool]:
    tools = []
    for name, ep in ENDPOINTS.items():
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        for param, desc in ep["params"].items():
            schema["properties"][param] = {"type": "string", "description": desc}
        tools.append(Tool(
            name=name,
            description=ep["description"],
            inputSchema=schema
        ))
    return tools

@SERVER.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name not in ENDPOINTS:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    ep = ENDPOINTS[name]
    url = f"{BASE_URL}{ep['path']}"
    
    async with httpx.AsyncClient(timeout=30) as client:
        if ep["method"] == "GET":
            resp = await client.get(url, params=arguments)
        else:
            resp = await client.post(url, json=arguments)
    
    result = {
        "status": resp.status_code,
        "data": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text[:2000]
    }
    
    if resp.status_code == 402:
        result["payment_required"] = True
        result["message"] = "This endpoint requires x402 payment. Send USDC on Base."
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]

async def main():
    async with stdio_server() as (read, write):
        await SERVER.run(read, write, SERVER.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
