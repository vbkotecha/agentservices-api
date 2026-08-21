# AgentServices Python SDK

**50 paid APIs for AI agents** — crypto data, DeFi yields, market intelligence, on-chain analytics, and more. Built-in x402 (USDC on Base) payments.

## Install

```bash
pip install agentservices

# With LangChain support:
pip install agentservices[langchain]

# With CrewAI support:
pip install agentservices[crewai]

# All integrations:
pip install agentservices[all]
```

## Quick Start

```python
from agentservices import AgentServicesClient

client = AgentServicesClient()

# Free endpoints
prices = client.get_prices("BTC,ETH,XRP")
sentiment = client.get_fear_greed()
news = client.get_news()

# Paid endpoints ($0.01-$0.25 per call via x402)
indicators = client.get_indicators("BTC")           # $0.02
portfolio = client.get_portfolio_intelligence("BTC") # $0.10
strategy = client.get_defi_strategy()                # $0.25
```

## LangChain Integration

```python
from agentservices import create_langchain_tools
from langchain.agents import create_react_agent

tools = create_langchain_tools()
agent = create_react_agent(llm, tools)

# Or select specific endpoints:
tools = create_langchain_tools(endpoints=["crypto_prices", "technical_indicators", "portfolio_intelligence"])
```

36 tools available covering all endpoints.

## CrewAI Integration

```python
from agentservices import create_crewai_tools
from crewai import Agent

tools = create_crewai_tools()
analyst = Agent(
    role='Senior Crypto Analyst',
    goal='Provide market intelligence using AgentServices data',
    tools=tools,
    llm=llm,
)
```

20 native CrewAI BaseTool subclasses.

## x402 Payments

Paid endpoints return HTTP 402 with payment requirements. The SDK auto-detects this:

```python
# Without wallet — get payment info:
client = AgentServicesClient()
result = client.get_indicators("BTC")
# Returns: {"x402_requires_payment": True, "accepts": [{...}]}

# With wallet — auto-pay:
client = AgentServicesClient(wallet_private_key="0x...")
result = client.get_indicators("BTC")
# Returns: {"rsi": 45.2, "macd": {...}, ...}
```

## Available Endpoints

### Free (12 endpoints)
- `get_prices` — Crypto prices (BTC, ETH, XRP, SOL)
- `get_fear_greed` — Fear & Greed sentiment index
- `get_geo` — IP geolocation
- `get_trending` — Trending tokens
- `get_gas` — Gas tracker
- `get_swap_quote` — DEX swap quotes
- `get_predictions` — Market predictions
- `get_news` — Crypto news
- `get_social_trending` — Social media trends
- `get_global_market` — Global market stats
- `list_policies` — Dispute templates
- `get_agent_context` — Agent context

### Paid — Data ($0.01-$0.05)
- `get_indicators` ($0.02) — Technical indicators (RSI, MACD, BB)
- `get_defi_yields` ($0.02) — DeFi yield rates
- `get_url_metadata` ($0.01) — URL metadata extraction
- `search` ($0.01) — Web search
- `get_token_risk` ($0.03) — Token risk assessment
- `get_crypto_signals` ($0.04) — Trading signals
- `get_yield_comparison` ($0.03) — Cross-protocol yield comparison
- `get_hn_sentiment` ($0.02) — Hacker News sentiment
- `get_npm_stats` ($0.02) — npm package stats
- `get_github_trending` ($0.02) — GitHub trending repos
- `get_whales` ($0.02) — Whale tracking
- `get_exchange_flows` ($0.02) — Exchange flows
- `get_defi_tvl` ($0.02) — DeFi TVL

### Paid — Bundled Intelligence ($0.05-$0.25)
- `deep_research` ($0.05) — Search + extract + synthesize
- `get_market_pulse` ($0.05) — Full market overview
- `get_portfolio_intelligence` ($0.10) — Price + signal + risk + sentiment
- `get_onchain_overview` ($0.15) — Whales + flows + correlation + TVL
- `get_defi_strategy` ($0.25) — Full DeFi investment strategy

### Paid — Marketing ($0.03-$0.05)
- `get_marketing_sentiment` ($0.03) — Brand sentiment
- `get_marketing_competitors` ($0.03) — Competitor analysis
- `get_content_gaps` ($0.03) — Content gap analysis
- `get_marketing_ad_copy` ($0.05) — AI ad copy generation

### Paid — Inference ($0.03)
- `inference` ($0.03) — AI inference (GPT models)
- `complete` ($0.03) — AI text completion

### Paid — Traditional Finance ($0.01-$0.02)
- `get_stock_quote` ($0.01) — Stock prices
- `get_stock_history` ($0.01) — Stock price history
- `get_fx_rates` ($0.01) — FX rates
- `get_commodities` ($0.02) — Gold, silver, oil

## Links

- **API Docs:** https://agentservices.to/docs
- **OpenAPI Spec:** https://agentservices.to/openapi.json
- **MCP Endpoint:** https://agentservices.to/mcp
- **GitHub:** https://github.com/vbkotecha/agentservices-api

## License

MIT
