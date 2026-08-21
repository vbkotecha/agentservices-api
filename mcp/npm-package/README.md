# agentservices-mcp

MCP server for [AgentServices](https://agentservices.to) — 50+ paid APIs for AI agents.

Crypto data, DeFi yields, on-chain analytics, portfolio intelligence, deep research, market intelligence, and more. x402 micropayments via USDC on Base.

## Install

```bash
# No install needed — use with npx
npx agentservices-mcp
```

## Configure

### Claude Desktop
Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "agentservices": {
      "command": "npx",
      "args": ["agentservices-mcp"]
    }
  }
}
```

### Cursor
Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "agentservices": {
      "command": "npx",
      "args": ["agentservices-mcp"]
    }
  }
}
```

### Windsurf
Add to MCP settings:

```json
{
  "mcpServers": {
    "agentservices": {
      "command": "npx",
      "args": ["agentservices-mcp"]
    }
  }
}
```

## Available Tools

### Free Endpoints (no payment required)
- `crypto_prices` — Current crypto prices
- `fear_greed` — Crypto Fear & Greed Index
- `trending_crypto` — Trending cryptocurrencies
- `global_market` — Global market stats
- `gas_prices` — Gas prices for major chains
- `swap_quote` — DEX swap quotes
- `crypto_news` — Latest crypto news
- `social_trending` — Trending social topics
- `list_policies` — Dispute resolution templates
- `crypto_predictions` — Price predictions
- `ip_geolocation` — IP geo lookup

### Paid Endpoints (x402 — USDC on Base)
- `technical_indicators` — RSI, MACD, Bollinger Bands ($0.02)
- `defi_yields` — DeFi yield rates ($0.02)
- `url_metadata` — Extract metadata from URLs ($0.01)
- `search_web` — AI-powered web search ($0.01)
- `whale_tracker` — Large transaction tracking ($0.02)
- `exchange_flows` — Exchange inflows/outflows ($0.02)
- `correlation_matrix` — Crypto correlations ($0.02)
- `stablecoin_flows` — Stablecoin flows ($0.02)
- `defi_tvl` — TVL across protocols ($0.02)
- `token_risk_score` — Token risk assessment ($0.03)
- `crypto_signals` — Aggregated trading signals ($0.04)
- `yield_comparison` — Risk-adjusted yield comparison ($0.03)
- `deep_research` — Search + extract + synthesize ($0.05)
- `portfolio_intelligence` — Full portfolio analysis ($0.10)
- `defi_strategy` — DeFi investment strategy ($0.25)
- `market_pulse` — Market direction signal ($0.05)
- `onchain_overview` — On-chain analytics bundle ($0.15)
- `ai_inference` — AI model inference ($0.03)
- `ai_complete` — AI text completion ($0.03)
- `resolve_dispute` — AI dispute resolution ($0.05)
- ...and more (50 tools total)

## How Payments Work

When you call a paid endpoint, the server returns a `402 Payment Required` response with x402 payment details. Agents with x402-compatible wallets (like Coinbase AgentKit) can automatically pay USDC on Base to complete the call.

Free endpoints work immediately — no wallet needed.

## Requirements

- Node.js 18+ (uses built-in `https` and `readline` — no npm dependencies)

## Links

- Website: [agentservices.to](https://agentservices.to)
- Examples: [agentservices.to/examples](https://agentservices.to/examples)
- MCP endpoint: `agentservices.to/mcp` (Streamable HTTP transport)
- GitHub: [github.com/vbkotecha/agentservices-api](https://github.com/vbkotecha/agentservices-api)

## License

MIT
