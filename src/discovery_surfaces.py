"""Public GEO/discovery copy for x402 REST payments and MCP tools."""

CANONICAL_HOST = "https://agentservices.to"
MCP_URL = f"{CANONICAL_HOST}/mcp"


def mcp_auth_metadata() -> dict:
    return {
        "type": "none",
        "note": "Free MCP tools require no auth. Paid services are available via x402-protected REST endpoints.",
    }


def mcp_pricing_metadata() -> dict:
    meta: dict = {
        "protocol": "x402",
        "currency": "USDC",
        "chain": "base",
        "rest": "Wallet agents pay via HTTP 402 on REST endpoints",
    }
    return meta


def payment_paths_metadata() -> dict:
    meta: dict = {
        "rest": {
            "protocol": "x402",
            "currency": "USDC",
            "chain": "base",
            "note": "Wallet agents pay per-request via HTTP 402 on REST endpoints",
        },
    }
    return meta


def ai_plugin_manifest() -> dict:
    auth = {"type": "none"}
    description_for_human = "Financial data APIs for AI agents. Paid REST calls use x402 USDC on Base."
    description_for_model = (
        "Paid APIs for AI agents. MCP at https://agentservices.to/mcp. "
        "Free tools are available through MCP; paid tools must be called via x402-protected REST endpoints."
    )

    return {
        "schema_version": "v1",
        "name_for_model": "agentservices",
        "name_for_human": "AgentServices",
        "description_for_model": description_for_model,
        "description_for_human": description_for_human,
        "auth": auth,
        "api": {"type": "openapi", "url": f"{CANONICAL_HOST}/openapi.json"},
        "logo_url": f"{CANONICAL_HOST}/favicon.ico",
        "contact_email": "vbkotecha@gmail.com",
        "legal_info_url": CANONICAL_HOST,
        "url": CANONICAL_HOST,
    }


def mcp_json() -> dict:
    description = (
        "MCP server at https://agentservices.to/mcp (Streamable HTTP). "
        "Free tools are available through MCP; paid services use x402 USDC on Base via REST. "
        "37+ tools across crypto, DeFi, stocks, research."
    )
    return {
        "name": "AgentServices",
        "version": "6.0.0",
        "description": description,
        "mcp_endpoint": MCP_URL,
        "transport": "streamable-http",
        "website": CANONICAL_HOST,
        "authentication": mcp_auth_metadata(),
        "payment": payment_paths_metadata(),
    }


def llms_txt_content(path_count: int) -> str:
    return f"""# AgentServices

> Paid APIs for AI agents. {path_count} live routes generated from the deployed OpenAPI schema. Data, search, market intelligence, inference, and ERC-8004 identity/reputation/evidence. Free tools are available via MCP; paid tools must be called through x402-protected REST endpoints (USDC on Base).

## Quick Start
- Free endpoints: GET https://agentservices.to/v1/prices (crypto prices), GET https://agentservices.to/v1/fear-greed (market sentiment)
- Paid endpoints: GET https://agentservices.to/v1/indicators/BTC (0.02 USDC), GET https://agentservices.to/v1/search?q=... (0.01 USDC)
- MCP server: {MCP_URL} (Streamable HTTP)
- Full docs: https://agentservices.to/docs
- OpenAPI spec: https://agentservices.to/openapi.json
- Health check: https://agentservices.to/health
- Task catalog: https://agentservices.to/v1/catalog/search?query=web+research
- Tool contract: https://agentservices.to/v1/catalog/tools/research.web
- Live capability schema: https://agentservices.to/openapi.json
- ERC-8004 provider metadata: https://agentservices.to/v1/erc8004/provider
- ERC-8004 agent discovery: https://agentservices.to/v1/erc8004/agents
## Key Endpoints
- [Crypto Prices](https://agentservices.to/v1/prices): Free. Real-time prices for 1000+ tokens.
- [Technical Indicators](https://agentservices.to/v1/indicators/BTC): $0.02. RSI, MACD, Bollinger, ATR, volume analysis.
- [DeFi Yields](https://agentservices.to/v1/yields): $0.02. Yield farming opportunities across protocols.
- [Search](https://agentservices.to/v1/search): $0.01. Web search with structured extraction.
- [Market Pulse](https://agentservices.to/v1/market-pulse): $0.05. Sentiment + trending + news + whales in one call.
- [On-Chain Overview](https://agentservices.to/v1/onchain-overview): $0.15. Whales + flows + correlation + TVL.
- [Portfolio Intelligence](https://agentservices.to/v1/portfolio): $0.10. Price + signal + risk + sentiment bundled.
- [DeFi Strategy](https://agentservices.to/v1/defi-strategy): $0.25. Full strategy report with recommendations.

## Payment (REST / wallet agents)
- Protocol: x402 (HTTP 402 Payment Required)
- Asset: USDC on Base (eip155:8453)
- Wallet: 0x9863aB6242663FCc84c33632741711dB78f8Fd15
- No API keys required for x402 REST

## Integration
- MCP: Add {MCP_URL} to your MCP client for free tools. Paid services must be called through x402-protected REST endpoints.
- Python SDK: pip install agentservices
- npm: npx agentservices-mcp
"""


def security_txt_content() -> str:
    return (
        "Contact: mailto:hustlemode@agentmail.to\n"
        "Expires: 2027-08-28T19:00:00.000Z\n"
        "Preferred-Languages: en\n"
        "Canonical: https://agentservices.to/.well-known/security.txt\n"
    )


def agents_txt_content(path_count: int) -> str:
    return f"""# AgentServices — Agent Instructions

## What This Service Does
AgentServices provides paid API endpoints for AI agents. The deployed schema currently exposes {path_count} routes covering crypto market data, on-chain analytics, DeFi intelligence, market sentiment, stock data, web extraction, AI inference, and ERC-8004 identity/reputation/evidence.

## How to Pay (REST / wallet agents)
1. Make a GET/POST request to any paid REST endpoint
2. Server responds with HTTP 402 + payment details (x402 protocol)
3. Sign payment with your wallet (USDC on Base)
4. Retry request with payment proof in header
5. Server verifies on-chain and returns data

## Free Endpoints (no payment needed)
- GET /v1/prices — Crypto prices
- GET /v1/fear-greed — Fear & Greed index
- GET /v1/trending — Trending tokens
- GET /v1/gas — Gas prices
- GET /v1/news — Crypto news
- GET /v1/global — Global market stats

## MCP Server
Endpoint: {MCP_URL}
Transport: Streamable HTTP
Tools: 38 (free + paid)
Auth: None for free tools. Paid tools are refused through MCP; use the corresponding x402-protected REST endpoint instead.
## Contact
Email: hustlemode@agentmail.to
Website: https://agentservices.to
"""
