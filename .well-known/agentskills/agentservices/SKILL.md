---
name: agentservices
description: >-
  Access paid data APIs for AI agents including crypto prices, technical indicators,
  DeFi yields, on-chain analytics (whale tracking, exchange flows, stablecoin flows),
  market intelligence (sentiment, trends, competitor analysis, content gaps, ad copy),
  portfolio intelligence, DeFi strategy optimization, web search and extraction,
  URL metadata, IP geolocation, AI inference (GPT models), fear-greed index, and
  MCP integration. Use when the agent needs real-time financial data, crypto market
  data, on-chain analysis, marketing intelligence, research, or AI inference.
  Payments via x402 protocol (USDC on Base). Free endpoints available for prices,
  trending, news, and social data.
license: MIT
compatibility: >-
  Network access required. Supports x402 micropayments (USDC on Base) for paid
  endpoints. Works with any HTTP client or MCP-compatible agent. No SDK installation
  required -- standard REST API with optional MCP transport.
metadata:
  author: AgentServices
  version: "5.3.0"
  website: "https://agentservices.to"
  api_base_url: "https://agentservices.to"
  repository: "https://github.com/vbkotecha/agentservices-api"
  documentation: "https://agentservices.to/docs"
  payment_protocol: "x402"
  payment_currency: "USDC"
  payment_network: "Base (eip155:8453)"
  payment_facilitator: "Coinbase CDP"
  total_services: "50"
  paid_services: "38"
  free_services: "12"
  mcp_tools: "36"
  mcp_endpoint: "https://agentservices.to/mcp"
---

# AgentServices -- Data APIs for AI Agents

## Overview

AgentServices provides 50 API endpoints for AI agents, covering crypto data,
on-chain analytics, market intelligence, web research, and AI inference.
Paid endpoints use x402 micropayments ($0.01-$0.25 per call in USDC on Base).
12 endpoints are completely free.

## Quick Start

### Free Endpoints (no payment needed)

```bash
# Crypto prices
curl https://agentservices.to/v1/prices
curl https://agentservices.to/v1/price/BTC

# Market sentiment
curl https://agentservices.to/v1/fear-greed

# Trending assets
curl https://agentservices.to/v1/trending

# Gas prices
curl https://agentservices.to/v1/gas

# News
curl https://agentservices.to/v1/news

# Social signals
curl https://agentservices.to/v1/social
```

### Paid Endpoints (x402 payment)

Paid endpoints return HTTP 402 with payment instructions. Use any x402-compatible
client (e.g., Coinbase agentic wallet) to complete payment automatically.

```python
import requests
from x402 import facilitate

# Example: Get crypto technical indicators
response = requests.get("https://agentservices.to/v1/indicators/BTC")
if response.status_code == 402:
    payment = facilitate(response.json())
    response = requests.get(
        "https://agentservices.to/v1/indicators/BTC",
        headers={"X-PAYMENT": payment.header, "X-402-RECIPIENT": payment.recipient}
    )
print(response.json())
```

## Endpoint Categories

### Crypto Data (Free + Paid)
| Endpoint | Price | Description |
|----------|-------|-------------|
| GET /v1/prices | Free | Top crypto prices |
| GET /v1/price/{symbol} | Free | Single asset price |
| GET /v1/fear-greed | Free | Fear & Greed index |
| GET /v1/indicators/{symbol} | $0.02 | RSI, MACD, moving averages |
| GET /v1/yields | $0.02 | Top DeFi yield pools |

### On-Chain Analytics (Paid)
| Endpoint | Price | Description |
|----------|-------|-------------|
| GET /v1/whales | $0.02 | Large wallet movements |
| GET /v1/exchange-flows | $0.02 | Exchange inflow/outflow |
| GET /v1/correlation | $0.03 | Asset correlation matrix |
| GET /v1/defi-tvl | $0.02 | DeFi Total Value Locked |
| GET /v1/stablecoin-flows | $0.02 | Stablecoin supply changes |
| GET /v1/onchain-overview | $0.15 | Bundled on-chain intelligence |

### Market Intelligence (Paid)
| Endpoint | Price | Description |
|----------|-------|-------------|
| POST /v1/marketing/sentiment | $0.03 | Brand sentiment analysis |
| POST /v1/marketing/trends | $0.03 | Market trend identification |
| POST /v1/marketing/competitors | $0.05 | Competitor analysis |
| POST /v1/marketing/content-gaps | $0.04 | Content opportunity discovery |
| POST /v1/marketing/ad-copy | $0.05 | AI-generated ad copy |
| GET /v1/market-pulse | $0.05 | Bundled market direction signal |

### Bundled Intelligence (Paid)
| Endpoint | Price | Description |
|----------|-------|-------------|
| GET /v1/research | $0.05 | Search + extract + synthesize |
| GET /v1/portfolio | $0.10 | Price + signal + risk + sentiment |
| GET /v1/defi-strategy | $0.25 | Yield optimization + risk assessment |
| GET /v1/onchain-overview | $0.15 | Whales + flows + TVL + correlation |

### Research & Web (Paid)
| Endpoint | Price | Description |
|----------|-------|-------------|
| GET /v1/search | $0.01 | Web search for agents |
| GET /v1/metadata | $0.01 | URL metadata extraction |

### AI Inference (Paid)
| Endpoint | Price | Description |
|----------|-------|-------------|
| POST /v1/inference | $0.03 | LLM inference (GPT models) |
| POST /v1/complete | $0.03 | Text completion |

### MCP Integration
Remote MCP transport via Streamable HTTP:
```
MCP_URL=https://agentservices.to/mcp
```
36 tools available. Compatible with Claude, Cursor, and any MCP client.

## Payment Setup

AgentServices uses the x402 protocol for micropayments. To use paid endpoints:

1. **Coinbase Agentic Wallet (recommended)**: Set up at wallet.coinbase.com
2. **Any x402 client**: Implement the x402 payment flow from the 402 response
3. **CDP Paymaster**: Payments are gasless (no ETH needed, only USDC)

## Use Cases

- **Portfolio Monitoring**: /v1/portfolio gives complete position analysis
- **DeFi Yield Optimization**: /v1/defi-strategy finds best yields with risk assessment
- **Market Intelligence**: /v1/market-pulse for directional signals
- **On-Chain Research**: /v1/onchain-overview for whale + flow analysis
- **Marketing Analysis**: /v1/marketing/* endpoints for competitive intelligence
- **AI Inference**: /v1/inference for LLM-powered analysis

## Support

- Docs: https://agentservices.to/docs
- GitHub: https://github.com/vbkotecha/agentservices-api
- MCP: https://agentservices.to/mcp
