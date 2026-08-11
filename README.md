# AgentServices

> 50-endpoint crypto, market intelligence, and AI inference API for AI agents — with x402 micropayments on Base

[![Version](https://img.shields.io/badge/version-5.3.0-brightgreen)](https://github.com/vbkotecha/agentservices-api)
[![Network](https://img.shields.io/badge/network-Base%20Mainnet-blue)](https://base.org)
[![Payment](https://img.shields.io/badge/payment-x402%20%2F%20USDC-purple)](https://x402.org)
[![MCP](https://img.shields.io/badge/MCP-compatible-orange)](https://modelcontextprotocol.io)
[![Status](https://img.shields.io/badge/status-live-success)](https://agentservices.to/health)

**Live at:** [agentservices.to](https://agentservices.to) | **MCP Server:** `https://agentservices.to/mcp` (Streamable HTTP) | **Discovery:** `/.well-known/x402`

## What is this?

AgentServices is the monetized API layer for AI agents. No API keys, no subscriptions — agents pay per-request with USDC on Base using the [x402 payment protocol](https://x402.org).

**50 endpoints** across crypto data, market intelligence, DeFi analytics, on-chain analytics, AI inference, portfolio intelligence, and dispute resolution. 12 are free. 38 are paid via x402 (from $0.002 to $0.25 per call).

## Buyer path: discover → try → pay → retain

Use the [buyer quickstart](docs/buyer-quickstart.md) for the complete path. The exact next action is to run the no-credential discovery check:

```bash
python3 examples/mcp_discovery_buyer_proof.py
```

Then follow the same buyer journey:

1. **Discover:** confirm the hosted MCP server and free tool catalog with the [MCP discovery proof](examples/mcp_discovery_buyer_proof.py).
2. **Try free:** retrieve a real price result with the [free SDK proof](examples/sdk_free_price_buyer_proof.js).
3. **Inspect the paid challenge:** decode the live 402 terms with the [paid SDK proof](examples/sdk_paid_indicator_buyer_proof.js). It never signs or settles payment.
4. **Buy an outcome:** pay the returned x402 terms, retry the same request, and retain the returned paid result. See the [token-risk](docs/token-risk-outcome-contract.md), [market-pulse](docs/market-pulse-outcome-contract.md), and [research-brief](docs/research-brief-outcome-contract.md) contracts for result limits and provenance.
5. **Retain evidence:** run the existing [receipt builder](examples/build_x402_receipt.py) with the original challenge, paid response, and your wallet authorization or transaction reference.

The four proofs have different limits: discovery and free SDK verify no-spend access; the paid SDK proof verifies challenge shape only; the receipt builder hashes buyer-held evidence and does not verify settlement. None of them claims adoption, settlement, or revenue.

For activation measurement definitions, see [Activation Metrics](docs/activation-metrics.md). To probe the live funnel, run `python3 examples/check_activation_funnel.py`.

## Endpoints

### Free (no payment required)
| Endpoint | Description |
|----------|-------------|
| `GET /v1/prices?symbols=BTC,ETH` | Current crypto prices (CoinGecko) |
| `GET /v1/trending` | Trending tokens by market activity |
| `GET /v1/global` | Global market cap, volume, BTC dominance |
| `GET /v1/fear-greed` | Crypto Fear & Greed sentiment index |
| `GET /v1/gas` | Current gas prices on Base/Ethereum |
| `GET /v1/predictions` | AI-generated market predictions |
| `GET /v1/news` | Latest crypto news headlines |
| `GET /v1/social/trending` | Trending social sentiment topics |
| `GET /v1/geo?ip=1.2.3.4` | IP geolocation lookup |
| `GET /v1/swap/quote?from=&to=&amount=` | DEX swap quote (0x integration) |
| `GET /v1/policies` | List dispute resolution policy templates |
| `GET /health` | API health check |

### Paid — Data APIs (x402)
| Endpoint | Price | Description |
|----------|-------|-------------|
| `GET /v1/indicators/BTC` | $0.02 | Technical indicators (RSI, MACD, Bollinger Bands, ATR, Support/Resistance) |
| `GET /v1/yields` | $0.02 | Top DeFi yield pools by TVL |
| `GET /v1/metadata?url=` | $0.01 | URL metadata extraction and unfurling |
| `GET /v1/search?q=` | $0.01 | Web search for crypto/market information |
| `GET /v1/onchain/:address` | $0.02 | On-chain analytics for any address |
| `GET /v1/onchain/:address/tokens` | $0.03 | Token holdings for any address |

### Paid — Synthesis APIs (x402)
| Endpoint | Price | Description |
|----------|-------|-------------|
| `GET /v1/token-risk/{token}` | $0.03 | Snapshot-based volatility, liquidity-proxy, and market-cap risk score |
| `GET /v1/crypto-signals` | $0.04 | Aggregated buy/sell signals across multiple indicators |
| `GET /v1/yield-comparison` | $0.03 | Compare yields across protocols with risk-adjusted returns |
| `GET /v1/hn-sentiment` | $0.02 | Hacker News sentiment analysis for tech topics |
| `GET /v1/npm-stats/:package` | $0.02 | NPM package download stats and trends |
| `GET /v1/github-trending` | $0.02 | Trending GitHub repos by language/topic |
| `GET /v1/marketing-intel` | $0.05 | Marketing intelligence: competitors, content gaps, ad copy |

### Paid — Bundled Intelligence (x402)
| Endpoint | Price | Description |
|----------|-------|-------------|
| `GET /v1/research?q=` | $0.05 | Deep research: search + extract + synthesize in one call |
| `GET /v1/portfolio?symbol=BTC` | $0.10 | Portfolio intelligence: price + signal + risk + sentiment + verdict |
| `GET /v1/defi-strategy` | $0.25 | DeFi strategy report: top yields + TVL + comparison + risk flags |
| `GET /v1/market-pulse` | $0.05 | Market pulse: fear-greed + trending + news + social + whales + global |
| `GET /v1/onchain-overview` | $0.15 | On-chain overview: whales + exchange flows + stablecoin flows + correlation + DeFi TVL |

### Paid — AI Inference (x402)
| Endpoint | Price | Description |
|----------|-------|-------------|
| `POST /v1/inference` | $0.03 | LLM inference (gpt-5.4/5.4-mini/5.5) — chat completions |
| `POST /v1/complete` | $0.03 | Text completion (CodexSale proxy) |

### Paid — Dispute Resolution (x402)
| Endpoint | Price | Description |
|----------|-------|-------------|
| `POST /v1/disputes` | $0.05 | AI-powered dispute resolution (7 policy templates) |

---

## Use Cases — What Agents Can Build

### Portfolio Monitor
```bash
# ALL-IN-ONE: Get portfolio intelligence in a single call ($0.10)
# Returns: price + technical signal + risk score + market sentiment + verdict
curl "https://agentservices.to/v1/portfolio?symbol=BTC"

# Or build it yourself from individual endpoints:
# Get current prices (FREE)
curl https://agentservices.to/v1/prices?symbols=BTC,ETH,SOL

# Get technical signals for entry/exit ($0.04)
curl https://agentservices.to/v1/crypto-signals

# Check snapshot-based token risk before buying ($0.03)
# Use a CoinGecko-compatible identifier for portable direct HTTP calls.
curl https://api.agentservices.to/v1/token-risk/pepe
# Contract and payment-receipt guidance: docs/token-risk-outcome-contract.md
```

### DeFi Yield Optimizer
```bash
# ALL-IN-ONE: Get DeFi strategy report ($0.25)
# Returns: top yields + protocol TVL + cross-chain comparison + risk flags
curl "https://agentservices.to/v1/defi-strategy"

# Get all yield pools ranked by TVL ($0.02)
curl https://agentservices.to/v1/yields

# Compare yields with risk-adjusted returns ($0.03)
curl https://agentservices.to/v1/yield-comparison

# Check on-chain position for any wallet ($0.02)
curl https://agentservices.to/v1/onchain/0x9863aB6242663FCc84c33632741711dB78f8Fd15
```

### Market Intelligence Agent
```bash
# ALL-IN-ONE: Get market pulse report ($0.05)
# Returns: fear-greed + trending + news + social + whales + global market
curl "https://agentservices.to/v1/market-pulse"

# Get market sentiment (FREE)
curl https://agentservices.to/v1/fear-greed

# Search for latest news on any topic ($0.01)
curl "https://agentservices.to/v1/search?q=base+chain+ecosystem"

# Get trending tokens (FREE)
curl https://agentservices.to/v1/trending

# Get marketing intelligence report ($0.05)
curl "https://agentservices.to/v1/marketing-intel?competitor=blockrun&topic=x402"
```

### Technical Analysis Bot
```bash
# Full technical indicator suite ($0.02)
curl https://agentservices.to/v1/indicators/BTC
# Returns: RSI, MACD, Bollinger Bands, ATR, Support/Resistance levels

# AI-generated market predictions (FREE)
curl https://agentservices.to/v1/predictions

# Combine with on-chain analytics ($0.03)
curl https://agentservices.to/v1/onchain/0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045/tokens
```

### Developer Research Agent
```bash
# GitHub trending repos ($0.02)
curl "https://agentservices.to/v1/github-trending?language=python&since=weekly"

# NPM package stats ($0.02)
curl https://agentservices.to/v1/npm-stats/react

# Hacker News sentiment ($0.02)
curl "https://agentservices.to/v1/hn-sentiment?q=AI+agents"
```

### AI Chat / Inference
```bash
# Chat completions via x402 ($0.03)
curl -X POST https://agentservices.to/v1/inference \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-5.4-mini","messages":[{"role":"user","content":"Explain x402 in 3 sentences"}]}'
```

### On-Chain Analytics
```bash
# ALL-IN-ONE: Get full on-chain overview ($0.15)
# Returns: whale movements + exchange flows + stablecoin flows + correlation matrix + DeFi TVL
curl "https://agentservices.to/v1/onchain-overview"

# On-chain analytics for any wallet ($0.02)
curl https://agentservices.to/v1/onchain/0x9863aB6242663FCc84c33632741711dB78f8Fd15

# Token holdings for any wallet ($0.03)
curl https://agentservices.to/v1/onchain/0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045/tokens
```

---

## Quick Start

### Using curl
```bash
# Free — no payment needed
curl https://agentservices.to/v1/prices?symbols=BTC,ETH

# Paid — returns HTTP 402 with payment instructions in the header
curl -i https://agentservices.to/v1/indicators/BTC
# Response includes x402 payment envelope: network, amount, payTo address
# Agent pays via x402 client, retries with X-Payment header, gets data
```

### Using as MCP Server (Claude Desktop, Cursor, etc.)
```json
{
  "mcpServers": {
    "agentservices": {
      "url": "https://agentservices.to/mcp",
      "transport": "streamable-http"
    }
  }
}
```

13+ MCP tools available: `crypto_prices`, `trending_tokens`, `global_market`, `gas_prices`, `market_predictions`, `crypto_news`, `social_trending`, `technical_indicators`, `defi_yields`, `search_web`, `token_risk`, `crypto_signals`, `onchain_analytics`, `deep_research`, `portfolio_intelligence`, `defi_strategy`, `market_pulse`, `onchain_overview`

### Using with Python
```python
import httpx

# Free endpoints
resp = httpx.get("https://agentservices.to/v1/prices?symbols=BTC,ETH")
prices = resp.json()

# Paid endpoints — use x402 client to handle payment
from x402.client import x402Client
client = x402Client()
result = client.get("https://agentservices.to/v1/indicators/BTC")
# Client handles 402 → pays USDC → retries with payment proof → returns data
```

### Using with JavaScript/TypeScript
```typescript
// Free endpoints
const prices = await fetch("https://agentservices.to/v1/prices?symbols=BTC,ETH").then(r => r.json());

// Paid endpoints — use @x402/facilitator
import { wrapFetchWithPayment } from "@x402/facilitator";
const paidFetch = wrapFetchWithPayment(fetch);
const indicators = await paidFetch("https://agentservices.to/v1/indicators/BTC").then(r => r.json());
```

## Dispute Resolution Engine

AgentServices includes an AI-powered dispute resolution system with 7 policy templates:

| Policy | Use Case |
|--------|----------|
| `freelance-delivery` | Freelancer vs client delivery disputes |
| `milestone-payment` | Milestone-based project payment disputes |
| `sla-monitoring` | Service level agreement violations |
| `api-quality` | API response quality / uptime disputes |
| `bug-bounty` | Bug bounty validity disputes |
| `scope-dispute` | Project scope creep disputes |
| `physical-commerce` | Physical goods transaction disputes |

## Discovery & Listings

- [x402 Discovery](https://agentservices.to/.well-known/x402) — Live
- [MCP Registry](https://registry.modelcontextprotocol.io) — Listed as `to.agentservices/agentservices`
- [CDP Bazaar](https://bazaar.coinbase.com) — Extension enabled
- [awesome-x402](https://github.com/xpaysh/awesome-x402) — PR submitted

## Tech Stack

- **FastAPI** (Python 3.11+)
- **x402 v2** payment middleware (Coinbase CDP facilitator)
- **USDC** on **Base Mainnet** (EIP-3009 gasless transfers)
- Deployed on Railway with custom domain + TLS

## Coinbase AgentKit Integration

AgentServices includes a built-in [Coinbase AgentKit](https://github.com/coinbase/agentkit) action provider (`agentkit/` directory). This lets any AgentKit agent use AgentServices APIs with typed, documented actions:

```python
from coinbase_agentkit import AgentKit, AgentKitConfig
from agentkit import agentservices_action_provider

agent_kit = AgentKit(AgentKitConfig(
    wallet_provider=wallet_provider,
    action_providers=[agentservices_action_provider()]
))
```

**18 actions** covering free (prices, fear-greed, trending, gas) and paid endpoints (indicators, DeFi yields, portfolio intelligence, research, onchain analytics, AI inference, and more). See [`agentkit/README.md`](agentkit/README.md) for full documentation.

## License

MIT — Build on it, fork it, integrate it.

## Links

- **API:** [agentservices.to](https://agentservices.to)
- **MCP:** [agentservices.to/mcp](https://agentservices.to/mcp)
- **Discovery:** [agentservices.to/.well-known/x402](https://agentservices.to/.well-known/x402)
- **GitHub:** [github.com/vbkotecha/agentservices-api](https://github.com/vbkotecha/agentservices-api)
- **x402 Protocol:** [x402.org](https://x402.org)
- **Base:** [base.org](https://base.org)
