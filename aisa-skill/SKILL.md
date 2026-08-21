# AgentServices — Paid APIs for AI Agents

> **Discovery:** AgentServices provides 50 endpoints (38 paid via x402) for crypto market data, DeFi intelligence, market intelligence, web search, AI inference, and on-chain analytics. Agents pay per call in USDC on Base — no API keys, no accounts.

## Quick Start

```python
# Install the x402 client
pip install x402-fetch

# Make a paid API call (agent wallet required)
import x402_fetch
response = x402_fetch.get(
    "https://agentservices.to/v1/portfolio?symbol=BTC",
    payer_wallet="0xYourWalletAddress"
)
print(response.json())
```

## What Agents Can Do

### Market Intelligence
- **GET /v1/portfolio?symbol=BTC** ($0.10) — Price + technical signal + risk score + market sentiment + AI verdict
- **GET /v1/research?q=your_query** ($0.05) — Web search + content extraction + AI synthesis in one call
- **GET /v1/market-pulse** ($0.05) — Fear & Greed + trending + news + social + whale activity + direction signal
- **GET /v1/defi-strategy** ($0.25) — Top yields + protocol TVL + cross-chain comparison + risk assessment
- **GET /v1/onchain-overview** ($0.15) — Whale movements + exchange flows + stablecoin flows + correlation + DeFi TVL

### Crypto Data
- **GET /v1/indicators/{symbol}** ($0.02) — RSI, MACD, Bollinger Bands, moving averages
- **GET /v1/defi-yields** ($0.02) — Top DeFi yield opportunities across chains
- **GET /v1/token-risk?address={addr}** ($0.03) — Rug/honeypot risk score for any token
- **GET /v1/crypto-signals?symbol={sym}** ($0.04) — Buy/sell signals from technical analysis
- **GET /v1/fx-rates** ($0.003) — Real-time forex rates

### Search & Research
- **GET /v1/search?q={query}** ($0.01) — Web search with relevance scoring
- **GET /v1/web-extract?url={url}** ($0.01) — Extract clean text from any webpage
- **GET /v1/hn-sentiment** ($0.02) — Hacker News sentiment analysis for tech trends

### Developer Intelligence
- **GET /v1/npm-stats?package={name}** ($0.02) — npm package download stats + security
- **GET /v1/github-trending** ($0.02) — GitHub trending repos by language
- **GET /v1/seo-keywords?domain={domain}** ($0.03) — SEO keyword analysis

### AI Inference
- **POST /v1/inference** ($0.03) — GPT-5.4/5.5 compatible chat completions
- **POST /v1/complete** ($0.03) — Quick completion endpoint

### Free Endpoints
- **GET /v1/prices** — Crypto prices (free)
- **GET /v1/fear-greed** — Fear & Greed Index (free)
- **GET /v1/trending** — Trending coins (free)
- **GET /v1/gas** — Current gas prices (free)
- **GET /v1/news** — Latest crypto news (free)
- **GET /v1/global** — Global market cap, BTC dominance (free)

## Payment

All paid endpoints use the **x402 protocol** (HTTP 402 Payment Required):
1. Agent sends request → server returns 402 with payment details
2. Agent signs USDC payment (EIP-3009) → resends with X-PAYMENT header
3. Server verifies → returns data

- **Network:** Base (eip155:8453)
- **Asset:** USDC (0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913)
- **Pay to:** 0x9863aB6242663FCc84c33632741711dB78f8Fd15
- **Gas:** Sponsored by CDP facilitator (no ETH needed, only USDC)

## MCP Integration

AgentServices also has an MCP endpoint for direct tool integration:
- **URL:** `https://agentservices.to/mcp`
- **Tools:** 36 MCP tools covering all endpoints
- **Transport:** Remote MCP via Streamable HTTP
- **Protocol version:** 2026-07-28 (server/discover supported)

## Use Cases

### Portfolio Monitor Agent
```
1. GET /v1/portfolio?symbol=BTC → full analysis
2. GET /v1/defi-strategy → yield opportunities
3. Alert if risk score > 7 or signal = "strong sell"
```

### Research Agent
```
1. GET /v1/research?q=latest+AI+regulations → search + extract + synthesize
2. GET /v1/hn-sentiment → tech community pulse
3. Compile findings
```

### Trading Agent
```
1. GET /v1/crypto-signals?symbol=ETH → buy/sell signals
2. GET /v1/token-risk?address=0x... → safety check
3. GET /v1/onchain-overview → whale activity
4. Execute trade
```

## Links
- **Website:** https://agentservices.to
- **API Docs:** https://agentservices.to/docs
- **OpenAPI Spec:** https://agentservices.to/openapi.json
- **MCP Registry:** to.aiservices/aiservices
- **x402 Manifest:** https://agentservices.to/.well-known/x402.json
- **GitHub:** github.com/vbkotecha/agentservices-api
