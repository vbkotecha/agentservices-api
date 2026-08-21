# AgentServices Action Provider for Coinbase AgentKit

[AgentServices](https://agentservices.to) provides 50+ paid APIs for AI agents — crypto data, market intelligence, DeFi analytics, onchain insights, web search, and AI inference. All paid endpoints use the x402 protocol (USDC micropayments on Base).

This action provider lets any [Coinbase AgentKit](https://github.com/coinbase/agentkit) agent discover and use AgentServices APIs.

## Installation

```bash
pip install agentservices-agentkit
```

## Quick Start

```python
from coinbase_agentkit import AgentKit, AgentKitConfig, CdpWalletProvider
from agentkit.agentservices_action_provider import agentservices_action_provider

wallet_provider = CdpWalletProvider(...)  # Your wallet provider

agent_kit = AgentKit(AgentKitConfig(
    wallet_provider=wallet_provider,
    action_providers=[
        agentservices_action_provider(),
    ]
))
```

## Available Actions

### Free Endpoints (no payment required)

| Action | Description |
|--------|-------------|
| `get_crypto_price` | Current price for any cryptocurrency |
| `get_batch_prices` | Prices for multiple cryptocurrencies |
| `get_fear_greed` | Crypto Fear & Greed Index (0-100) |
| `get_trending` | Trending cryptocurrencies |
| `get_gas_prices` | Ethereum gas prices (slow/standard/fast) |
| `get_global_market` | Global crypto market cap, volume, BTC dominance |

### Paid Endpoints (x402 / USDC on Base)

| Action | Price | Description |
|--------|-------|-------------|
| `get_market_indicators` | $0.02 | RSI, MACD, Bollinger Bands, moving averages |
| `get_defi_yields` | $0.02 | Top DeFi yield opportunities across protocols |
| `get_token_risk` | $0.03 | Rug/honeypot checks, liquidity analysis |
| `get_crypto_signals` | $0.04 | Aggregated buy/sell/hold trading signals |
| `get_ai_inference` | $0.03 | GPT-5.4/5.5 inference for any text task |
| `search_web` | $0.01 | Web search with titles, URLs, snippets |
| `get_stock_quote` | $0.01 | Stock market quotes (AAPL, GOOGL, etc.) |
| `get_fx_rates` | $0.003 | Foreign exchange rates for 30+ currencies |
| `get_market_pulse` | $0.05 | Comprehensive market overview (6 data sources) |
| `get_deep_research` | $0.05 | Web research + extraction + synthesis |
| `get_portfolio_intelligence` | $0.10 | Price + signals + risk + sentiment + verdict |
| `get_onchain_overview` | $0.15 | Whales + flows + correlations + TVL |
| `get_defi_strategy` | $0.25 | Full DeFi investment strategy report |

## How x402 Payments Work

AgentServices uses the [x402 protocol](https://x402.org) for payments:

1. Agent calls a paid endpoint
2. Server responds with HTTP 402 (Payment Required) + price + payment address
3. Agent's wallet signs a USDC payment on Base
4. Server verifies payment and returns data

AgentKit's `CdpWalletProvider` handles wallet operations. For x402 specifically, agents need a small USDC balance (~$1 covers hundreds of calls).

## Competitive Comparison

| Feature | AgentServices | Alchemy |
|---------|--------------|---------|
| Crypto market data | 50 services | None (chain RPC only) |
| Market intelligence | Sentiment, trends, competitors | None |
| AI inference | GPT-5.4/5.5 proxy | None |
| Free tier | 6 free endpoints | None |
| Price transparency | Full price list | Opaque credit system |
| Bundled endpoints | 5 high-value bundles | None |
| Blockchain RPC | None | Full JSON-RPC, 100+ chains |

**AgentServices and Alchemy are complementary.** Use Alchemy for raw chain data, AgentServices for analytics and intelligence.

## Links

- Website: [agentservices.to](https://agentservices.to)
- API: [agentservices.to/v1/](https://agentservices.to/docs)
- Examples: [agentservices.to/examples](https://agentservices.to/examples)
- MCP: [agentservices.to/mcp](https://agentservices.to/mcp)
- x402 Discovery: [agentservices.to/.well-known/x402.json](https://agentservices.to/.well-known/x402.json)
- AgentSkills: [agentservices.to/.well-known/agentskills/agentservices/SKILL.md](https://agentservices.to/.well-known/agentskills/agentservices/SKILL.md)
- GitHub: [github.com/vbkotecha/agentservices-api](https://github.com/vbkotecha/agentservices-api)
