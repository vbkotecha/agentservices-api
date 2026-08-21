---
name: agentservices
description: Access paid APIs for AI agents — crypto market data, DeFi intelligence, portfolio analysis, and 37 MCP tools. Agents discover and pay for data via x402 (USDC on Base). Use when the user needs crypto prices, technical indicators, DeFi yields, whale tracking, market sentiment, portfolio intelligence, deep research, or any financial data API.
---

# AgentServices — Paid APIs for AI Agents

## Overview
AgentServices provides 53 API endpoints (41 paid) for AI agents. Agents pay per-request using x402 micropayments (USDC on Base). No API keys needed — payment IS authentication.

## Free Endpoints (no payment required)
- `GET /v1/price/{symbol}` — Current crypto price (BTC, ETH, SOL, etc.)
- `GET /v1/prices?symbols=BTC,ETH` — Batch prices
- `GET /v1/fear-greed` — Crypto Fear & Greed index
- `GET /v1/gas` — Ethereum gas prices
- `GET /v1/trending` — Trending tokens
- `GET /v1/news` — Latest crypto news
- `GET /v1/global` — Global market stats

## Paid Endpoints (x402 / USDC on Base)
- `GET /v1/indicators/{symbol}` ($0.02) — RSI, MACD, Bollinger Bands, ATR, Support/Resistance
- `GET /v1/yields` ($0.02) — Top DeFi yield pools by TVL
- `GET /v1/whales` ($0.02) — Large whale transactions (BTC ≥10, ETH)
- `GET /v1/exchange-flows` ($0.02) — CEX reserve flows
- `GET /v1/correlation` ($0.03) — 30-day correlation matrix
- `GET /v1/defi-tvl` ($0.02) — Top DeFi protocols by TVL
- `GET /v1/token-risk/{symbol}` ($0.03) — Token risk scoring
- `GET /v1/portfolio?symbol=BTC` ($0.10) — Portfolio intelligence (price + signal + risk + sentiment)
- `GET /v1/market-pulse` ($0.05) — Market snapshot (Fear & Greed + trending + news + whales + global)
- `POST /v1/deep-research` ($0.05) — Deep research brief on any topic
- `GET /v1/stock-quote?symbol=AAPL` ($0.02) — Real-time stock prices
- `GET /v1/fx` ($0.003) — FX rates for 30+ currencies
- `GET /v1/web-extract?url=...` ($0.002) — Extract clean text from any URL

## MCP Endpoint
Connect directly: `https://agentservices.to/mcp` (37 tools, Streamable HTTP)

## How to Pay
1. Make a request to any paid endpoint
2. Receive HTTP 402 with payment details
3. Pay using x402-compatible wallet (USDC on Base)
4. Retry with payment proof
5. Receive data

## Base URL
`https://agentservices.to`
