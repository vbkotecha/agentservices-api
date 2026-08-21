# AgentServices vs Competitors

> How AgentServices compares to other x402-paid API providers for AI agents.

## Quick Comparison

| Feature | AgentServices | Superhighway | BlockRun | x402 Generic Data APIs |
|---------|--------------|-------------|----------|----------------------|
| **Total Endpoints** | 47 | 5 | ~12 | 1-3 each |
| **Paid Endpoints** | 35 | 5 | ~8 | 1-3 |
| **Price Range** | $0.002–$0.10 | $0.001–$0.005 | $0.01–$0.05 | $0.01–$0.50 |
| **Crypto Data** | ✅ Prices, indicators, signals, risk | ❌ | ✅ Limited | Varies |
| **DeFi Analytics** | ✅ Yields, TVL, comparison, stablecoin flows | ❌ | ❌ | Rare |
| **On-Chain Data** | ✅ Whales, exchange flows, correlation | ❌ | ❌ | Rare |
| **AI Inference** | ✅ gpt-5.4/5.5 gateway | ❌ | ✅ Primary offering | Some |
| **Market Intelligence** | ✅ Sentiment, trends, competitors, ad copy | ❌ | ❌ | ❌ |
| **Web Search** | ✅ $0.01 | ✅ $0.001–0.002 | ❌ | Some |
| **Deep Research** | ✅ Search + Extract + Synthesize ($0.05) | ✅ Search + Scrape ($0.005) | ❌ | ❌ |
| **Portfolio Intelligence** | ✅ Price + Signal + Risk + Sentiment ($0.10) | ❌ | ❌ | ❌ |
| **Traditional Finance** | ✅ Stocks, SEC, commodities, FX, economics | ❌ | ❌ | Rare |
| **Dispute Resolution** | ✅ Policy-based ($0.05) | ❌ | ❌ | ❌ |
| **MCP Compatible** | ✅ 32 tools via Streamable HTTP | ✅ MCP | ❌ | Some |
| **Package Security** | ✅ PyPI/npm scanning | ❌ | ❌ | ❌ |
| **SEO Research** | ✅ Keyword volume + competition | ❌ | ❌ | ❌ |

## Competitive Advantages

### 1. Breadth — We're the "API Toolkit," Not a Single Tool
AgentServices covers 8 categories: crypto, DeFi, on-chain, inference, search, research, traditional finance, and security. Most competitors offer 1-2 categories. An agent building a trading bot can get price data, technical signals, risk scores, on-chain whale tracking, AND market sentiment — all from one API.

### 2. Bundled High-Value Endpoints
- **Portfolio Intelligence ($0.10):** Replaces 4+ API calls — price + technical signal + risk score + market sentiment + synthesized verdict
- **Deep Research ($0.05):** Search + extract + synthesize in one call
- **Yield Comparison ($0.03):** DeFi yields with risk-adjusted analysis

### 3. MCP-Native
Full MCP server (32 tools) via Streamable HTTP with 2026-07-28 spec compliance. Agents using Claude Desktop, Cursor, ChatGPT, Codex, or Windsurf can connect directly.

### 4. Price Tiering
From $0.002 (web extraction) to $0.10 (portfolio intelligence). Agents can start free (12 free endpoints) and scale up. Competitive on search ($0.01 vs Superhighway's $0.001 — but we offer synthesis and broader coverage).

---

## Detailed Competitor Analysis

### Superhighway (superhighway.walls.sh)
- **What:** Personal project by Pat Walls. SearXNG + x402 + MCP.
- **Endpoints:** 5 (search, scrape, AI, convert, screenshots)
- **Price:** $0.001–$0.005 per call
- **Strength:** Cheapest search+scrape on x402. Clean MCP integration.
- **Weakness:** No crypto, no DeFi, no on-chain, no inference, no market intelligence. Single-person project.
- **Our Edge:** 9x more endpoints, 8 categories vs 1. We compete on value (bundled endpoints) where they compete on price (raw search).

### BlockRun (blockrun.xyz)
- **What:** AI inference marketplace — gpt models via x402.
- **Endpoints:** ~12 (mostly LLM inference + some data)
- **Price:** $0.01–$0.05 per call
- **Strength:** Focused inference provider. Multiple LLM models.
- **Weakness:** Limited data endpoints. No crypto-specific or DeFi analytics. No MCP.
- **Our Edge:** We have our OWN inference gateway (gpt-5.4/5.5) PLUS 35 data endpoints. One-stop shop.

### Generic x402 Data APIs (individual Bazaar listings)
- **What:** Single-purpose APIs (e.g., "BTC price API," "weather API")
- **Price:** $0.01–$0.50 per call
- **Strength:** Deep specialization in one thing.
- **Weakness:** Agents must integrate 10+ different APIs to build anything useful. Different auth, different response formats, different payment flows.
- **Our Edge:** Unified API surface, consistent response format, single x402 payment integration, MCP endpoint for zero-config agent integration.

---

## Market Positioning

**AgentServices is the "Stripe API" for AI agents — one integration, everything you need.**

While competitors sell individual tools (search, inference, price data), AgentServices sells a complete intelligence toolkit. Agents don't want to integrate 12 APIs. They want one endpoint that gives them everything.

### Revenue Tier Strategy
Based on x402 market research (July 2026):
- 95% of x402 transaction value is in calls >$1.00
- Our prices ($0.002–$0.10) target volume, not margin
- **Strategy:** Use low-price data endpoints as customer acquisition, upsell to bundled intelligence ($0.05–$0.10) and eventually premium tiers ($0.50–$1.00)
- **Next bundled endpoints:** DeFi Strategy Report ($1.00), Enterprise Market Intelligence ($0.50)

---

## Pricing Philosophy

| Tier | Price Range | Purpose | Examples |
|------|------------|---------|----------|
| **Free** | $0.00 | Customer acquisition | Prices, fear-greed, trending, gas, news |
| **Micro** | $0.001–$0.01 | Raw data commodity | Search, metadata, FX, extraction |
| **Standard** | $0.02–$0.05 | Analyzed/synthesized data | Indicators, signals, risk, research |
| **Premium** | $0.05–$0.10 | Bundled intelligence | Portfolio intelligence, marketing reports |
| **Enterprise** | $0.50+ | Future tier | Strategy reports, custom analytics |
