# @agentservices/plugin-elizaos

**ElizaOS plugin** exposing the [AgentServices API](https://agentservices.to) as agent actions. 50+ endpoints covering crypto data, market intelligence, on-chain analytics, DeFi strategy, portfolio intelligence, AI inference, and web search — all via [x402](https://x402.org) micropayments on Base Mainnet.

[![ElizaOS](https://img.shields.io/badge/elizaOS-compatible-orange)](https://elizaos.github.io)
[![x402 v2](https://img.shields.io/badge/x402-v2-00D395)](https://www.x402.org)
[![Base Mainnet](https://img.shields.io/badge/network-Base%20Mainnet-0052FF)](https://basescan.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

## What this plugin does

Adds **12 actions** and **1 passive provider** to any ElizaOS agent. The agent can query live crypto prices, technical indicators, DeFi yields, portfolio intelligence, market overview, on-chain analytics, deep research, and web search — paying per request in USDC on Base Mainnet.

No API keys. No subscriptions. Just fund a wallet with USDC and your agent can access premium market data on demand.

## Install

```bash
npm install @agentservices/plugin-elizaos
```

## Usage

In your agent character file:

```typescript
import { agentservicesPlugin } from '@agentservices/plugin-elizaos';

export const character = {
  name: 'CryptoAnalyst',
  // ... other config
  plugins: [agentservicesPlugin],
  settings: {
    AGENTSERVICES_BUYER_PRIVATE_KEY: process.env.BUYER_WALLET_KEY, // 0x...
    AGENTSERVICES_BASE_URL: 'https://agentservices.to', // optional, this is the default
  },
};
```

## Actions

These trigger when the user mentions relevant keywords:

| Action | Price | Trigger phrases |
|--------|-------|----------------|
| `GET_CRYPTO_PRICES` | FREE | "crypto prices", "bitcoin price", "eth price" |
| `GET_TECHNICAL_INDICATORS` | $0.02 | "RSI", "MACD", "technical analysis", "TA" |
| `GET_DEFI_YIELDS` | $0.02 | "DeFi yields", "best yield", "staking", "farming" |
| `GET_FEAR_GREED` | FREE | "fear and greed", "market sentiment" |
| `GET_PORTFOLIO_INTELLIGENCE` | $0.10 | "portfolio analysis", "investment analysis" |
| `GET_MARKET_PULSE` | $0.05 | "market overview", "market summary", "market snapshot" |
| `GET_DEFI_STRATEGY` | $0.25 | "DeFi strategy", "yield strategy", "DeFi report" |
| `GET_ONCHAIN_OVERVIEW` | $0.15 | "onchain", "whales", "exchange flows", "chain analytics" |
| `DO_RESEARCH` | $0.05 | "research", "investigate", "look up" |
| `WEB_SEARCH` | $0.01 | "search", "find", "look up" |
| `GET_TRENDING` | FREE | "trending", "hot coins" |
| `GET_CRYPTO_NEWS` | FREE | "news", "headlines", "latest news" |

## Provider

`agentservices_market_context` — passively injects current BTC/ETH prices into every agent turn. Gives your agent constant awareness of market state without explicit queries.

## Payment modes

**Without `AGENTSERVICES_BUYER_PRIVATE_KEY`** — actions throw "Payment required" with the 402 details. The agent will tell the user how much each query costs.

**With `AGENTSERVICES_BUYER_PRIVATE_KEY`** — plugin auto-signs ERC-3009 `TransferWithAuthorization` using viem. Each query costs $0.01–$0.25 USDC. Fund the buyer wallet with $5 → good for hundreds of queries.

No ETH required on the buyer wallet — the AgentServices facilitator pays settlement gas.

## Example agent conversation

```
User:  What are BTC and ETH doing right now?
Agent: [executes GET_CRYPTO_PRICES — FREE]
       Bitcoin is at $63,976, Ethereum at $2,082.

User:  Give me a full portfolio analysis of SOL
Agent: [executes GET_PORTFOLIO_INTELLIGENCE — $0.10]
       Portfolio Intelligence: SOL
       Price: $142.50
       Signal: BULLISH — above EMA 50, RSI 58 (neutral-bullish)
       Risk Score: 42/100 (moderate)
       Sentiment: Positive — social mentions up 23%

       Verdict: SOL shows moderate bullish momentum with manageable
       risk. Key resistance at $148. Consider scaling in on dips
       toward EMA support at $138.

User:  What's the on-chain picture?
Agent: [executes GET_ONCHAIN_OVERVIEW — $0.15]
       On-Chain Overview:
       Whale activity: 3 large transfers to exchanges detected
       Exchange flows: Net outflow $4.2M (bullish)
       Stablecoin flows: USDC inflows +$12M to exchanges
       DeFi TVL: $4.2B across protocols

User:  Research the latest developments with Solana DeFi
Agent: [executes DO_RESEARCH — $0.05]
       Research: "Solana DeFi developments"
       [Full synthesized report with sources]
```

## Full Endpoint Catalog

AgentServices has 50 endpoints (11 free, 39 paid). This plugin exposes the 12 most useful actions. For the complete catalog, see:

- **Website**: [agentservices.to](https://agentservices.to)
- **API Docs**: [agentservices.to/docs](https://agentservices.to/docs)
- **MCP Endpoint**: `agentservices.to/mcp` (36 tools)
- **OpenAPI Spec**: [agentservices.to/openapi.json](https://agentservices.to/openapi.json)

## License

MIT
