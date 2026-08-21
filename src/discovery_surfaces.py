"""Public GEO/discovery copy — ChatGPT MCP connector + x402 REST wallet path."""
from human_billing.config import credits_enabled, oauth_enabled, public_base_url

CANONICAL_HOST = "https://agentservices.to"
MCP_URL = f"{CANONICAL_HOST}/mcp"


def _base_url() -> str:
    return public_base_url() or CANONICAL_HOST


def mcp_auth_metadata() -> dict:
    base = _base_url()
    if oauth_enabled():
        return {
            "type": "oauth2",
            "note": "Google OAuth for humans in ChatGPT/Claude. Wallet agents use x402 on REST.",
            "authorization_server": f"{base}/.well-known/oauth-authorization-server",
            "protected_resource": f"{base}/.well-known/oauth-protected-resource",
        }
    return {
        "type": "none",
        "note": "Free tools require no auth. Paid REST uses x402 (HTTP 402) payment.",
    }


def mcp_pricing_metadata() -> dict:
    meta: dict = {
        "protocol": "x402",
        "currency": "USDC",
        "chain": "base",
        "rest": "Wallet agents pay via HTTP 402 on REST endpoints",
    }
    if credits_enabled():
        meta["mcp_human"] = "Google OAuth + Stripe prepaid credits"
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
    if oauth_enabled():
        human: dict = {
            "auth": "Google OAuth",
            "mcp_url": MCP_URL,
            "transport": "streamable-http",
            "note": "ChatGPT connector: sign in with Google for MCP",
        }
        if credits_enabled():
            human["billing"] = "Stripe prepaid credits"
            human["ledger"] = "stripe_customer_balance"
        meta["mcp_human"] = human
    return meta


def ai_plugin_manifest() -> dict:
    base = _base_url()
    if oauth_enabled():
        auth = {
            "type": "oauth",
            "authorization_url": f"{base}/oauth/authorize",
            "authorization_content_type": "application/x-www-form-urlencoded",
            "scope": "openid email profile mcp",
            "client_url": f"{base}/oauth/register",
        }
        description_for_human = (
            "MCP connector for ChatGPT: Google OAuth sign-in and Stripe prepaid credits. "
            "REST wallet agents pay via x402 USDC on Base."
        )
        description_for_model = (
            "Connect MCP at https://agentservices.to/mcp (Streamable HTTP). "
            "Humans in ChatGPT use Google OAuth and Stripe prepaid credits for paid MCP tools. "
            "Wallet agents use x402 USDC on Base for REST endpoints. "
            "37+ tools: crypto prices, DeFi, stocks, research, inference, on-chain analytics."
        )
    else:
        auth = {"type": "none"}
        description_for_human = "Financial data APIs for AI agents. Wallet agents pay via x402 USDC on Base."
        description_for_model = (
            "Paid APIs for AI agents. MCP at https://agentservices.to/mcp. "
            "Paid REST endpoints use x402 (USDC on Base)."
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
        "MCP connector at https://agentservices.to/mcp (Streamable HTTP). "
        "ChatGPT/human path: Google OAuth + Stripe credits. "
        "Wallet agents: x402 USDC on Base for REST. 37+ tools across crypto, DeFi, stocks, research."
    )
    return {
        "name": "AgentServices",
        "version": "5.3.0",
        "description": description,
        "mcp_endpoint": MCP_URL,
        "transport": "streamable-http",
        "website": CANONICAL_HOST,
        "authentication": mcp_auth_metadata(),
        "payment": payment_paths_metadata(),
    }


def llms_txt_content(path_count: int) -> str:
    oauth_block = ""
    if oauth_enabled():
        base = _base_url()
        credits_line = ""
        if credits_enabled():
            credits_line = (
                "- Billing: Stripe prepaid credits (ledger: stripe_customer_balance)\n"
            )
        oauth_block = f"""
## ChatGPT / Human Connector (MCP)
- MCP URL: {MCP_URL} (Streamable HTTP)
- Auth: Google OAuth (sign in with Google)
{credits_line}- OAuth discovery: {base}/.well-known/oauth-authorization-server
- Protected resource: {base}/.well-known/oauth-protected-resource

"""

    return f"""# AgentServices

> Paid APIs for AI agents. {path_count} live routes generated from the deployed OpenAPI schema. Data, search, market intelligence, inference, and ERC-8004 identity/reputation/evidence. ChatGPT connector via MCP (Google OAuth + Stripe credits). Wallet agents pay per call via x402 (USDC on Base).

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
{oauth_block}
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
- MCP: Add {MCP_URL} to your MCP client (ChatGPT connector or Claude/Cursor)
- Python SDK: pip install agentservices
- npm: npx agentservices-mcp
"""


def agents_txt_content(path_count: int) -> str:
    mcp_auth = (
        "Google OAuth + Stripe credits for ChatGPT/human MCP users. "
        "Wallet agents pay via x402 on REST."
        if oauth_enabled()
        else "None for free tools. Paid tools use x402 on REST."
    )
    credits_note = ""
    if oauth_enabled() and credits_enabled():
        credits_note = "Billing ledger: stripe_customer_balance (Stripe prepaid credits).\n"

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

## MCP Server (ChatGPT connector)
Endpoint: {MCP_URL}
Transport: Streamable HTTP
Tools: 38 (free + paid)
Auth: {mcp_auth}
{credits_note}
## Contact
Email: hustlemode@agentmail.to
Website: https://agentservices.to
"""
