# AIServices Developer Integration Guide

> How to integrate AIServices APIs into your AI application in under 5 minutes.

## Table of Contents
1. [Quick Start: Remote MCP](#quick-start-remote-mcp)
2. [Python SDK](#python-sdk)
3. [LangChain Integration](#langchain-integration)
4. [Direct HTTP / curl](#direct-http--curl)
5. [CrewAI Integration](#crewai-integration)
6. [Payments: How x402 Works](#payments-how-x402-works)
7. [Rate Limits & Pricing](#rate-limits--pricing)

---

## Quick Start: Remote MCP

The fastest way to get started. No installation required — connect your AI tool directly to our hosted MCP server.

### Claude Desktop
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "aiservices": {
      "url": "https://agentservices.to/mcp"
    }
  }
}
```

### Cursor IDE
Settings → MCP Servers → Add:
```
URL: https://agentservices.to/mcp
```

### Any MCP Client
```
MCP Server URL: https://agentservices.to/mcp
Transport: Streamable HTTP
```

**That's it.** 8 tools are now available: crypto prices, technical indicators, DeFi yields, fear & greed, IP geolocation, URL metadata, dispute resolution, and policy listing.

---

## Python SDK

```bash
pip install aiservices
```

### Free Endpoints
```python
from aiservices import AIServicesClient

client = AIServicesClient()

# Crypto prices
prices = client.get_prices("BTC,ETH,SOL,XRP")
# → {"BTC": {"price": 43250.00, "change_24h": 2.3}, ...}

# Fear & Greed
fg = client.get_fear_greed()
# → {"value": 72, "label": "Greed"}

# IP Geolocation
geo = client.get_geo("1.2.3.4")
# → {"country": "US", "city": "San Francisco", ...}
```

### Paid Endpoints (x402)
```python
# With x402 client for automatic payment
from aiservices import AIServicesClient
from x402.client import X402Client

x402 = X402Client(wallet="0x...")  # Your Base wallet
client = AIServicesClient(payment_client=x402)

# Technical indicators ($0.02)
indicators = client.get_indicators("BTC")
# → {"rsi": 58.2, "bollinger": {...}, "atr": 1234.5, ...}

# DeFi yields ($0.02)
yields = client.get_defi_yields()
# → {"pools": [{"protocol": "Aave", "apy": 4.2, "tvl": 1200000000}, ...]}

# Dispute resolution ($0.05)
ruling = client.resolve_dispute(
    policy="freelance-delivery",
    claimant="0xabc...",
    respondent="0xdef...",
    claim="Freelancer delivered work 2 weeks late",
    evidence=["contract_link", "email_thread"]
)
# → {"ruling": "partially_favors_claimant", "remedy": "...", "confidence": 0.82}
```

---

## LangChain Integration

```python
from aiservices import create_aiservices_tools
from langchain.agents import create_react_agent
from langchain_openai import ChatOpenAI

# Create all 8 tools at once
tools = create_aiservices_tools()

# Use with any LangChain agent
llm = ChatOpenAI(model="gpt-4")
agent = create_react_agent(llm, tools)

# Now your agent can:
# - Check crypto prices
# - Analyze market sentiment
# - Look up IP geolocation
# - Extract URL metadata
# - Resolve disputes
```

### Custom Tool Selection
```python
from aiservices.tools import CryptoPriceTool, FearGreedTool

# Pick only what you need
tools = [CryptoPriceTool(), FearGreedTool()]
```

---

## Direct HTTP / curl

### Free endpoints
```bash
# Single price
curl https://api.agentservices.to/v1/price/BTC

# Batch prices
curl "https://api.agentservices.to/v1/prices?symbols=BTC,ETH,SOL"

# Fear & Greed
curl https://api.agentservices.to/v1/fear-greed

# IP Geolocation
curl https://api.agentservices.to/v1/geo/1.2.3.4

# List dispute policies
curl https://api.agentservices.to/v1/policies
```

### Paid endpoints (returns 402 first)
```bash
# Technical indicators
curl https://api.agentservices.to/v1/indicators/BTC
# → HTTP 402 with payment-required header

# DeFi yields
curl https://api.agentservices.to/v1/yields

# URL metadata
curl "https://api.agentservices.to/v1/metadata?url=https://example.com"
```

---

## CrewAI Integration

```python
from crewai import Agent, Task, Crew
from aiservices import create_aiservices_tools

tools = create_aiservices_tools()

analyst = Agent(
    role="Crypto Analyst",
    goal="Analyze market conditions and provide insights",
    backstory="Expert crypto market analyst",
    tools=tools
)

task = Task(
    description="Check BTC price, RSI, and market sentiment. Give a buy/hold/sell signal.",
    agent=analyst
)

crew = Crew(agents=[analyst], tasks=[task])
result = crew.kickoff()
```

---

## Payments: How x402 Works

AIServices uses the [x402 protocol](https://x402.org) for micropayments. No API keys, no subscriptions.

### How it works:
1. Agent requests a paid endpoint
2. Server returns HTTP 402 with payment details (amount, wallet, network)
3. Agent's x402 client creates a USDC payment on Base
4. Server verifies payment via CDP facilitator
5. Server returns the data

### Payment amounts:
| Endpoint | Price |
|----------|-------|
| Technical indicators | $0.02 |
| DeFi yields | $0.02 |
| URL metadata | $0.01 |
| Dispute resolution | $0.05 |

All payments in **USDC on Base Mainnet** (chain ID 8453).

---

## Rate Limits & Pricing

| Tier | Requests/min | Notes |
|------|-------------|-------|
| Free | 60/min | No payment needed |
| Paid | 100/min | Per-request x402 payment |

**No signup required for free endpoints.** Just call the URL.

---

## Support

- **Docs:** [api.agentservices.to/docs](https://api.agentservices.to/docs)
- **GitHub:** [github.com/vbkotecha/agentservices-api](https://github.com/vbkotecha/agentservices-api)
- **Issues:** [GitHub Issues](https://github.com/vbkotecha/agentservices-api/issues)

## License

MIT — Build freely.
