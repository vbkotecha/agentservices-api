"""
AgentServices — Paid APIs for AI agents
Crypto market data, IP geolocation, URL metadata, marketing intelligence
"""
import os
import html
import json
from pathlib import Path

# Load .env file
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().strip().splitlines():
        if "=" in line and not line.startswith("#"):
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

from fastapi import FastAPI, Request, Query, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from typing import List
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crypto_data import get_price, get_multi_price, get_indicators, get_fear_greed, get_defi_yields
from geo_data import get_ip_geo
from web_data import get_url_metadata
from search_data import web_search
from dex_data import get_swap_quote, get_trending_tokens, get_gas_tracker
from prediction_data import get_polymarket_markets, get_polymarket_market, get_prediction_summary
from news_data import get_crypto_news, get_social_trending, get_global_market
from engine.policy_engine import evaluate_dispute, list_policies
from mcp_endpoint import router as mcp_router
from marketing_data import (
    SentimentRequest, TrendRequest, CompetitorRequest, ContentGapRequest, AdCopyRequest,
    analyze_sentiment, detect_trends, analyze_competitors, find_content_gaps, generate_ad_copy,
)
from onchain_data import (
    get_whales, get_exchange_flows, get_correlation_matrix,
    get_defi_tvl, get_stablecoin_flows, get_github_velocity, get_agent_context, get_macro,
)
from synthesis_data import (
    get_token_risk, get_crypto_signal, get_hn_sentiment, get_npm_stats,
    get_github_trending, get_yield_comparison, deep_research, portfolio_intelligence,
    defi_strategy_report, market_pulse, onchain_overview, arbitrage_scanner, liquidation_map,
)
from inference_gateway import list_models as list_inference_models, inference, quick_complete, chat_completions, list_all_openrouter_models
from pricing_cache import calculate_price as calc_dynamic_price, fetch_pricing, pricing_summary
from tradfi_data import get_stock_quote, get_stock_history, get_sec_filings, get_commodities, get_economic_indicators, get_fx_rates
from gov_data import get_ca_entity_status
from utility_data import extract_web_content, scan_package_security, seo_keywords, backlink_intelligence
from agent_memory import store as mem_store, retrieve as mem_retrieve, list_keys as mem_list, delete as mem_delete, search as mem_search
from skill_packs import crypto_dossier, stock_dossier, market_overview, available_skills
from media_gateway import generate_image, text_to_speech, multi_model_inference, list_all_models
from voice_gateway import get_phone_number, make_call, lookup_number
from agent_catalog import search_catalog, get_tool
from agent_identity import (register_agent, get_agent, add_feedback, reputation,
                            verify_agent, snapshot, verify_evidence, check_claims)
import erc8004_provider

AISERVICES_PAY_TO = "0x9863aB6242663FCc84c33632741711dB78f8Fd15"
WALLET = os.environ.get("WALLET_ADDRESS", AISERVICES_PAY_TO)
INDEXNOW_KEY = "42b652cb-203a-42db-8a86-4e94fbfcbeae"

app = FastAPI(
    title="AgentServices",
    version="5.3.0",
    docs_url=None,
    redoc_url=None,
    contact={
        "name": "AgentServices",
        "url": "https://agentservices.to",
    },
    license_info={
        "name": "MIT",
        "url": "https://github.com/vbkotecha/agentservices-api",
    },
    description="""Paid APIs for AI agents — data, intelligence, inference, and more.
Crypto market data, DeFi yields, DEX quotes, prediction markets, news, search, IP geolocation,
URL metadata, on-chain analytics, whale tracking, correlation matrix, DeFi TVL, stablecoin flows,
GitHub trending, npm stats, Hacker News sentiment, token risk scoring, crypto signals,
LLM inference gateway, marketing intelligence, and more.

All paid endpoints use x402 protocol with USDC on Base.
""",
)

class DynamicBodyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method == "POST" and request.url.path in ("/v1/chat/completions", "/v1/inference", "/v1/complete"):
            try:
                body = json.loads(await request.body())
                request.scope.setdefault("state", {})["dynamic_body"] = body
            except Exception:
                request.scope.setdefault("state", {})["dynamic_body"] = {}
        return await call_next(request)

app.add_middleware(DynamicBodyMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Security Headers + Bazaar Discovery Enrichment ---
# x402 indexers (CDP Bazaar / agentic.market) validate resources by GETting
# the live 402 response and checking for extensions.bazaar and
# resource.serviceName/tags. Without these, resources stay stuck in
# "processing" and never get indexed. This middleware enriches all 402
# responses with the required bazaar discovery metadata.
_BAZAAR_TAGS = ["data", "crypto", "defi", "search", "inference", "marketing-intelligence", "onchain", "analytics"]

# --- Bazaar Discovery Info Lookup Table ---
# CDP Bazaar probes endpoints using declared example inputs. Without proper
# bazaar.info (input/output/routeTemplate/schema), probes fail and endpoints
# stay invisible. This maps route patterns to discovery metadata.
# AgentForge reported: fixing this went from 2/16 to 15/16 indexed in hours.
_BAZAAR_ENDPOINT_INFO = {
    "/v1/indicators": {"method": "GET", "route": "/v1/indicators/:symbol", "path_params": {"symbol": "BTC"}, "query": {}, "body": None,
        "output_example": {"symbol": "BTC", "rsi": 45.2, "bollinger_bands": {"upper": 68500, "middle": 67000, "lower": 65500}, "atr": 1200}},
    "/v1/yields": {"method": "GET", "route": "/v1/yields", "path_params": {}, "query": {"chain": "ethereum"}, "body": None,
        "output_example": [{"protocol": "Aave V3", "asset": "USDC", "apy": 4.52, "tvl": 1200000000}]},
    "/v1/metadata": {"method": "GET", "route": "/v1/metadata", "path_params": {}, "query": {"url": "https://example.com"}, "body": None,
        "output_example": {"title": "Example", "description": "Sample metadata", "og_image": "https://example.com/img.png"}},
    "/v1/search": {"method": "GET", "route": "/v1/search", "path_params": {}, "query": {"q": "bitcoin price"}, "body": None,
        "output_example": [{"title": "Bitcoin Price", "url": "https://example.com", "snippet": "Current BTC price..."}]},
    "/v1/disputes": {"method": "POST", "route": "/v1/disputes", "path_params": {}, "query": {}, "body": {"dispute_type": "transaction", "description": "Sample dispute"},
        "output_example": {"dispute_id": "dsp_123", "status": "filed", "verdict": "pending"}},
    "/v1/marketing/sentiment": {"method": "POST", "route": "/v1/marketing/sentiment", "path_params": {}, "query": {}, "body": {"topic": "AI agents", "sources": ["twitter", "reddit"]},
        "output_example": {"topic": "AI agents", "sentiment_score": 0.72, "volume": 15420}},
    "/v1/marketing/trends": {"method": "POST", "route": "/v1/marketing/trends", "path_params": {}, "query": {}, "body": {"keywords": ["AI", "crypto"], "region": "US"},
        "output_example": [{"keyword": "AI agents", "trend_score": 89, "change": "+12%"}]},
    "/v1/marketing/competitors": {"method": "POST", "route": "/v1/marketing/competitors", "path_params": {}, "query": {}, "body": {"domain": "example.com", "keywords": ["API", "data"]},
        "output_example": [{"domain": "competitor.com", "overlap": 45, "gaps": ["blockchain"]}]},
    "/v1/marketing/content-gaps": {"method": "POST", "route": "/v1/marketing/content-gaps", "path_params": {}, "query": {}, "body": {"domain": "example.com", "topic": "AI"},
        "output_example": [{"keyword": "AI agent security", "difficulty": 35, "volume": 2400}]},
    "/v1/marketing/ad-copy": {"method": "POST", "route": "/v1/marketing/ad-copy", "path_params": {}, "query": {}, "body": {"product": "AgentServices", "audience": "developers", "tone": "professional"},
        "output_example": {"headlines": ["Build Faster with AgentServices"], "descriptions": ["50+ paid API endpoints for AI agents"]}},
    "/v1/whales": {"method": "GET", "route": "/v1/whales", "path_params": {}, "query": {"symbol": "BTC", "min_usd": "100000"}, "body": None,
        "output_example": [{"symbol": "BTC", "amount_usd": 5000000, "type": "buy", "exchange": "Binance"}]},
    "/v1/exchange-flows": {"method": "GET", "route": "/v1/exchange-flows", "path_params": {}, "query": {"symbol": "ETH"}, "body": None,
        "output_example": {"symbol": "ETH", "inflow_24h": 125000000, "outflow_24h": 98000000, "net_flow": -27000000}},
    "/v1/correlation": {"method": "GET", "route": "/v1/correlation", "path_params": {}, "query": {"symbols": "BTC,ETH,LINK"}, "body": None,
        "output_example": {"matrix": {"BTC-ETH": 0.85, "BTC-LINK": 0.62, "ETH-LINK": 0.71}}},
    "/v1/defi-tvl": {"method": "GET", "route": "/v1/defi-tvl", "path_params": {}, "query": {"chain": "ethereum"}, "body": None,
        "output_example": [{"protocol": "Lido", "tvl": 32000000000, "chain": "Ethereum"}]},
    "/v1/stablecoin-flows": {"method": "GET", "route": "/v1/stablecoin-flows", "path_params": {}, "query": {"chain": "ethereum"}, "body": None,
        "output_example": {"chain": "Ethereum", "inflow": 450000000, "outflow": 380000000}},
    "/v1/macro": {"method": "GET", "route": "/v1/macro", "path_params": {}, "query": {}, "body": None,
        "output_example": {"gdp_growth": 2.1, "inflation": 3.2, "unemployment": 4.1, "fed_rate": 5.25}},
    "/v1/inference": {"method": "POST", "route": "/v1/inference", "path_params": {}, "query": {}, "body": {"model": "gpt-5.4-mini", "messages": [{"role": "user", "content": "Hello"}]},
        "output_example": {"model": "gpt-5.4-mini", "choices": [{"message": {"role": "assistant", "content": "Hello! How can I help?"}}]}},
    "/v1/complete": {"method": "POST", "route": "/v1/complete", "path_params": {}, "query": {}, "body": {"model": "gpt-5.4-mini", "prompt": "What is Bitcoin?"},
        "output_example": {"model": "gpt-5.4-mini", "text": "Bitcoin is a decentralized digital currency..."}},
    "/v1/token-risk": {"method": "GET", "route": "/v1/token-risk/:token", "path_params": {"token": "bitcoin"}, "query": {}, "body": None,
        "output_example": {"token": "bitcoin", "risk_score": 15, "risk_label": "Low", "dimensions": {"volatility": 6.2, "market_cap_risk": 10, "liquidity_risk": 42.0}, "market_data": {"price_usd": 64000, "change_24h_pct": 2.1, "volume_24h_usd": 28000000000, "market_cap_usd": 1250000000000}, "momentum": "bullish", "recommendation": "Stable", "timestamp": "2026-08-07T00:00:00Z"}},
    "/v1/crypto-signals": {"method": "GET", "route": "/v1/crypto-signals", "path_params": {}, "query": {"symbol": "BTC"}, "body": None,
        "output_example": {"symbol": "BTC", "signal": "BULLISH", "strength": 72, "indicators": {"rsi": 45, "macd": "positive"}}},
    "/v1/yield-comparison": {"method": "GET", "route": "/v1/yield-comparison", "path_params": {}, "query": {"asset": "USDC"}, "body": None,
        "output_example": [{"protocol": "Aave V3", "apy": 4.52}, {"protocol": "Compound V3", "apy": 3.89}]},
    "/v1/hn-sentiment": {"method": "GET", "route": "/v1/hn-sentiment", "path_params": {}, "query": {"topic": "AI"}, "body": None,
        "output_example": {"topic": "AI", "avg_sentiment": 0.65, "post_count": 142, "top_keywords": ["agents", "LLM", "automation"]}},
    "/v1/portfolio": {"method": "GET", "route": "/v1/portfolio", "path_params": {}, "query": {"symbol": "BTC"}, "body": None,
        "output_example": {"symbol": "BTC", "price": 64000, "signal": "BULLISH", "risk": "LOW", "verdict": "Hold with confidence"}},
    "/v1/defi-strategy": {"method": "GET", "route": "/v1/defi-strategy", "path_params": {}, "query": {}, "body": None,
        "output_example": {"top_yields": [{"protocol": "Aave", "apy": 4.5}], "tvl_comparison": {}, "risk_assessment": "MODERATE"}},
    "/v1/market-pulse": {"method": "GET", "route": "/v1/market-pulse", "path_params": {}, "query": {}, "body": None,
        "output_example": {"research_type": "market_pulse", "modules": {"sentiment": {"fear_greed_value": 72, "fear_greed_label": "Greed", "interpretation": "Greed — market confident"}, "trending": {"data": []}}, "errors": [], "timestamp": "2026-08-07T00:00:00Z", "synthesis": {"market_direction": "BULLISH — Greed building. Trend continuation likely.", "sentiment_score": 72, "data_modules_active": 2, "modules_available": ["sentiment", "trending"]}, "pricing_advantage": "Informational pricing comparison."}},
    "/v1/onchain-overview": {"method": "GET", "route": "/v1/onchain-overview", "path_params": {}, "query": {}, "body": None,
        "output_example": {"whales": [], "exchange_flows": {}, "stablecoin_flows": {}, "defi_tvl": {}}},
    "/v1/arbitrage": {"method": "GET", "route": "/v1/arbitrage", "path_params": {}, "query": {"symbol": "BTC"}, "body": None,
        "output_example": {"symbol": "BTC", "spreads": [{"exchange_a": "Coinbase", "exchange_b": "CoinGecko", "spread_pct": 0.12}]}},
    "/v1/liquidation-map": {"method": "GET", "route": "/v1/liquidation-map", "path_params": {}, "query": {"symbols": "BTC,ETH"}, "body": None,
        "output_example": {"liquidation_zones": [{"symbol": "BTC", "protocols": {"Aave V3": {"liquidation_price": 55000}}}], "cascading_risk": "LOW"}},
    "/v1/research": {"method": "GET", "route": "/v1/research", "path_params": {}, "query": {"q": "Bitcoin ETF flows"}, "body": None,
        "output_example": {"query": "Bitcoin ETF flows", "sources": [], "synthesis": "ETF inflows have accelerated..."}},
    "/v1/web-extract": {"method": "POST", "route": "/v1/web-extract", "path_params": {}, "query": {}, "body": {"url": "https://example.com"},
        "output_example": {"url": "https://example.com", "content": "Extracted text...", "title": "Example"}},
    "/v1/package-security": {"method": "GET", "route": "/v1/package-security", "path_params": {}, "query": {"package": "express", "version": "4.18.0"}, "body": None,
        "output_example": {"package": "express", "vulnerabilities": [], "score": 95}},
    "/v1/seo-keywords": {"method": "GET", "route": "/v1/seo-keywords", "path_params": {}, "query": {"domain": "example.com", "topic": "AI"}, "body": None,
        "output_example": [{"keyword": "AI API", "volume": 12000, "difficulty": 45}]},
    "/v1/deep-research": {"method": "GET", "route": "/v1/deep-research", "path_params": {}, "query": {"q": "DeFi liquidation risks"}, "body": None,
        "output_example": {"query": "DeFi liquidation risks", "analysis": "Deep research findings...", "sources": []}},
    "/v1/github-velocity": {"method": "GET", "route": "/v1/github-velocity", "path_params": {}, "query": {"repo": "langchain-ai/langchain"}, "body": None,
        "output_example": {"repo": "langchain-ai/langchain", "commits_7d": 142, "stars": 95000, "velocity_trend": "UP"}},
    # --- Additional endpoints for full Bazaar coverage (Heartbeat #7, Jul 13 2026) ---
    "/v1/price": {"method": "GET", "route": "/v1/price/:symbol", "path_params": {"symbol": "BTC"}, "query": {}, "body": None,
        "output_example": {"symbol": "BTC", "price": 64250.50, "change_24h": 2.34, "volume_24h": 28000000000}},
    "/v1/prices": {"method": "GET", "route": "/v1/prices", "path_params": {}, "query": {"symbols": "BTC,ETH,SOL"}, "body": None,
        "output_example": [{"symbol": "BTC", "price": 64250.50}, {"symbol": "ETH", "price": 3180.20}, {"symbol": "SOL", "price": 145.60}]},
    "/v1/fx": {"method": "GET", "route": "/v1/fx", "path_params": {}, "query": {}, "body": None,
        "output_example": {"USD/EUR": 0.92, "USD/GBP": 0.79, "USD/JPY": 149.50, "EUR/GBP": 0.86}},
    "/v1/fx-rates": {"method": "GET", "route": "/v1/fx-rates", "path_params": {}, "query": {"base": "USD"}, "body": None,
        "output_example": {"base": "USD", "rates": {"EUR": 0.92, "GBP": 0.79, "JPY": 149.50, "CAD": 1.36}}},
    "/v1/gov/us/ca/entity": {"method": "GET", "route": "/v1/gov/us/ca/entity", "path_params": {}, "query": {"q": "202150010654"}, "body": None,
        "output_example": {"sku": "ca.entity.status", "name": "Pure Moon LLC", "entity_number": "202150010654", "type": "Limited Liability Company - CA", "status": "Active", "jurisdiction": "CALIFORNIA", "registered_agent": {"name": "Sierra Pearson", "city": "SACRAMENTO", "state": "CA"}, "initial_filing_date": "2021-12-06", "source": "California Secretary of State Business Entity Public Search API", "retrieved_at": "2026-08-16T00:00:00Z", "disclaimer": "This information is sourced from public records and is not legal or tax advice."}},
    "/v1/stocks": {"method": "GET", "route": "/v1/stocks/:ticker", "path_params": {"ticker": "AAPL"}, "query": {}, "body": None,
        "output_example": {"ticker": "AAPL", "price": 227.50, "change": 1.23, "volume": 52000000, "market_cap": 3450000000000}},
    "/v1/sec": {"method": "GET", "route": "/v1/sec/:ticker", "path_params": {"ticker": "AAPL"}, "query": {}, "body": None,
        "output_example": {"ticker": "AAPL", "filings": [{"type": "10-K", "date": "2024-11-01", "url": "https://sec.gov/..."}]}},
    "/v1/signals": {"method": "GET", "route": "/v1/signals/:symbol", "path_params": {"symbol": "BTC"}, "query": {}, "body": None,
        "output_example": {"symbol": "BTC", "signal": "BUY", "strength": 78, "indicators": {"rsi": 42, "macd": "bullish_cross", "ema": "above"}}},
    "/v1/security": {"method": "GET", "route": "/v1/security/:package", "path_params": {"package": "express"}, "query": {"version": "4.18.0"}, "body": None,
        "output_example": {"package": "express", "vulnerabilities": [], "score": 95, "last_audit": "2024-01-15"}},
    "/v1/npm-stats": {"method": "GET", "route": "/v1/npm-stats/:package", "path_params": {"package": "react"}, "query": {}, "body": None,
        "output_example": {"package": "react", "weekly_downloads": 25000000, "version": "19.0.0", "license": "MIT"}},
    "/v1/news": {"method": "GET", "route": "/v1/news", "path_params": {}, "query": {"category": "crypto"}, "body": None,
        "output_example": [{"title": "Bitcoin hits new high", "source": "CoinDesk", "url": "https://...", "published": "2024-01-15T10:00:00Z"}]},
    "/v1/global": {"method": "GET", "route": "/v1/global", "path_params": {}, "query": {}, "body": None,
        "output_example": {"total_market_cap": 2500000000000, "total_volume": 120000000000, "market_cap_change_24h": 2.5, "btc_dominance": 52.3}},
    "/v1/trending": {"method": "GET", "route": "/v1/trending", "path_params": {}, "query": {}, "body": None,
        "output_example": [{"id": "bitcoin", "name": "Bitcoin", "symbol": "BTC", "market_cap_rank": 1, "score": 100}]},
    "/v1/fear-greed": {"method": "GET", "route": "/v1/fear-greed", "path_params": {}, "query": {}, "body": None,
        "output_example": {"value": 72, "classification": "Greed", "timestamp": "2024-01-15T00:00:00Z"}},
    "/v1/commodities": {"method": "GET", "route": "/v1/commodities", "path_params": {}, "query": {}, "body": None,
        "output_example": {"gold": 2050.30, "silver": 23.45, "oil_wti": 78.20, "natural_gas": 2.85, "copper": 3.92}},
    "/v1/economic": {"method": "GET", "route": "/v1/economic", "path_params": {}, "query": {}, "body": None,
        "output_example": {"gdp_growth": 2.1, "inflation_rate": 3.2, "unemployment": 4.1, "fed_rate": 5.25, "cpi": 312.5}},
    "/v1/social": {"method": "GET", "route": "/v1/social", "path_params": {}, "query": {"symbol": "BTC"}, "body": None,
        "output_example": {"symbol": "BTC", "twitter_mentions": 45000, "reddit_subscribers": 6500000, "sentiment": "bullish"}},
    "/v1/gas": {"method": "GET", "route": "/v1/gas", "path_params": {}, "query": {"chain": "ethereum"}, "body": None,
        "output_example": {"chain": "ethereum", "slow": 12, "standard": 15, "fast": 18, "price_usd": 0.45}},
    "/v1/extract": {"method": "POST", "route": "/v1/extract", "path_params": {}, "query": {}, "body": {"url": "https://example.com"},
        "output_example": {"url": "https://example.com", "title": "Example", "content": "Extracted text...", "author": "John Doe"}},
    "/v1/chat/completions": {"method": "POST", "route": "/v1/chat/completions", "path_params": {}, "query": {}, "body": {"model": "gpt-5.4-mini", "messages": [{"role": "user", "content": "Hello"}]},
        "output_example": {"id": "chatcmpl-123", "model": "gpt-5.4-mini", "choices": [{"message": {"role": "assistant", "content": "Hello!"}}]}},
    "/v1/images/generations": {"method": "POST", "route": "/v1/images/generations", "path_params": {}, "query": {}, "body": {"model": "dall-e-3", "prompt": "A futuristic city"},
        "output_example": {"created": 1705312200, "data": [{"url": "https://..."}]}},
    "/v1/audio/speech": {"method": "POST", "route": "/v1/audio/speech", "path_params": {}, "query": {}, "body": {"model": "tts-1", "input": "Hello world", "voice": "alloy"},
        "output_example": {"audio_format": "mp3", "duration_seconds": 2.5, "size_bytes": 40000}},
    "/v1/models": {"method": "GET", "route": "/v1/models", "path_params": {}, "query": {}, "body": None,
        "output_example": {"models": [{"id": "gpt-5.4-mini", "provider": "openai"}, {"id": "claude-4-sonnet", "provider": "anthropic"}]}},
    "/v1/predictions": {"method": "GET", "route": "/v1/predictions", "path_params": {}, "query": {}, "body": None,
        "output_example": [{"slug": "btc-2024", "title": "BTC price prediction", "prediction": "$75K by Q4", "confidence": 0.72}]},
    "/v1/agent-context": {"method": "GET", "route": "/v1/agent-context", "path_params": {}, "query": {"q": "Bitcoin price trends"}, "body": None,
        "output_example": {"context": "Bitcoin has shown strong upward momentum...", "sources": [{"type": "market_data", "url": "..."}]}},
    "/v1/geo": {"method": "GET", "route": "/v1/geo/:ip", "path_params": {"ip": "8.8.8.8"}, "query": {}, "body": None,
        "output_example": {"ip": "8.8.8.8", "city": "Mountain View", "region": "CA", "country": "US", "lat": 37.4056, "lon": -122.0775}},
    "/v1/phone": {"method": "GET", "route": "/v1/phone", "path_params": {}, "query": {"number": "+14155551234"}, "body": None,
        "output_example": {"number": "+14155551234", "valid": True, "carrier": "Verizon", "line_type": "mobile", "country": "US"}},
    "/v1/swap/quote": {"method": "GET", "route": "/v1/swap/quote", "path_params": {}, "query": {"from": "USDC", "to": "ETH", "amount": "1000"}, "body": None,
        "output_example": {"from": "USDC", "to": "ETH", "amount_in": "1000", "amount_out": "0.314", "price_impact": "0.01%", "route": ["Uniswap V3"]}},
    "/v1/calls": {"method": "POST", "route": "/v1/calls", "path_params": {}, "query": {}, "body": {"to": "+14155551234", "message": "Hello"},
        "output_example": {"call_id": "call_123", "status": "queued", "duration_estimate": 30}},
    "/v1/memory/search": {"method": "POST", "route": "/v1/memory/search", "path_params": {}, "query": {}, "body": {"query": "BTC analysis"},
        "output_example": {"results": [{"key": "btc_analysis", "content": "BTC is showing..."}]}},
    "/v1/skills/crypto-dossier": {"method": "POST", "route": "/v1/skills/crypto-dossier", "path_params": {}, "query": {}, "body": {"symbol": "BTC"},
        "output_example": {"symbol": "BTC", "price": 64250, "analysis": "Bullish", "risk": "LOW", "signals": {}}},
    "/v1/skills/stock-dossier": {"method": "POST", "route": "/v1/skills/stock-dossier", "path_params": {}, "query": {}, "body": {"ticker": "AAPL"},
        "output_example": {"ticker": "AAPL", "price": 227.50, "analysis": "Strong buy", "pe_ratio": 32.5, "signals": {}}},
    "/v1/github-trending": {"method": "GET", "route": "/v1/github-trending", "path_params": {}, "query": {"language": "python"}, "body": None,
        "output_example": [{"repo": "langchain-ai/langchain", "stars": 95000, "language": "Python", "description": "Building applications with LLMs"}]},
    "/v1/seo/keywords": {"method": "GET", "route": "/v1/seo/keywords", "path_params": {}, "query": {"domain": "example.com", "topic": "AI"}, "body": None,
        "output_example": [{"keyword": "AI API", "volume": 12000, "difficulty": 45}]},
    "/v1/backlinks": {"method": "GET", "route": "/v1/backlinks", "path_params": {}, "query": {"domain": "example.com", "site_url": "https://example.com/"}, "body": None,
        "output_example": {"domain": "example.com", "status": "ok", "count": 2, "referring_domains": ["example.org", "github.com"], "backlinks": [{"url": "https://example.org/docs", "referring_domain": "example.org", "evidence": "target domain link found in page"}, {"url": "https://github.com/example/list/blob/main/README.md", "referring_domain": "github.com", "evidence": "target domain link found in file"}]}},
    "/v1/models/all": {"method": "GET", "route": "/v1/models/all", "path_params": {}, "query": {}, "body": None,
        "output_example": {"providers": ["openai", "anthropic", "google", "deepseek"], "models": [{"id": "gpt-5.4-mini", "context": 128000}]}},
    "/v1/skills/market-overview": {"method": "GET", "route": "/v1/skills/market-overview", "path_params": {}, "query": {}, "body": None,
        "output_example": {"fear_greed": 72, "trending": ["BTC", "SOL"], "top_gainers": [{"symbol": "SOL", "change": "+12%"}]}},
    "/v1/policies": {"method": "GET", "route": "/v1/policies", "path_params": {}, "query": {}, "body": None,
        "output_example": {"policies": [{"id": "rate_limit", "type": "throttle", "limit": 100}]}},
}

def _match_bazaar_info(route_path):
    """Match a route path to its bazaar info entry."""
    # Remove query string
    path = route_path.split("?")[0]
    # Try exact prefix match (longest first)
    for prefix, info in sorted(_BAZAAR_ENDPOINT_INFO.items(), key=lambda x: -len(x[0])):
        if path.startswith(prefix):
            return info
    return None

def _json_schema_from_example(value):
    """Best-effort JSON Schema fragment from an example value."""
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if isinstance(value, str):
        return {"type": "string"}
    if isinstance(value, list):
        item_schema = _json_schema_from_example(value[0]) if value else {}
        return {"type": "array", "items": item_schema or {"type": "object"}}
    if isinstance(value, dict):
        properties = {k: _json_schema_from_example(v) for k, v in value.items()}
        return {"type": "object", "properties": properties}
    return {}

def _build_bazaar_schema(info_data):
    """Build OneSource-shaped JSON Schema (Draft 2020-12) for bazaar.info."""
    method = info_data.get("method", "GET").upper()
    query_methods = {"GET", "HEAD", "DELETE"}
    body_methods = {"POST", "PUT", "PATCH"}
    method_enum = sorted(query_methods if method in query_methods else body_methods)

    input_props = {
        "type": {"type": "string", "const": "http"},
        "method": {"type": "string", "enum": method_enum},
    }
    input_required = ["type", "method"]

    if info_data.get("path_params"):
        path_props = {k: {"type": "string"} for k in info_data["path_params"]}
        input_props["pathParams"] = {
            "type": "object",
            "properties": path_props,
            "required": list(path_props),
        }

    if method in query_methods and info_data.get("query"):
        query_props = {k: {"type": "string"} for k in info_data["query"]}
        input_props["query"] = {"type": "object", "properties": query_props}

    if method in body_methods and info_data.get("body") is not None:
        input_props["bodyType"] = {"type": "string", "enum": ["json", "form-data", "text"]}
        input_props["body"] = _json_schema_from_example(info_data["body"])
        input_required.extend(["bodyType", "body"])

    info_props = {
        "input": {
            "type": "object",
            "properties": input_props,
            "required": input_required,
            "additionalProperties": False,
        }
    }
    info_required = ["input"]

    if info_data.get("output_example") is not None:
        info_props["output"] = {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "example": {"type": "object"},
            },
            "required": ["type"],
        }

    if info_data.get("route"):
        info_props["routeTemplate"] = {"type": "string"}

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": info_props,
        "required": info_required,
    }

def _build_bazaar_extension(route_path, route_desc):
    """Build the full bazaar extension with discovery info for CDP Bazaar indexing."""
    base = {
        "name": "AgentServices",
        "description": route_desc,
    }
    info_data = _match_bazaar_info(route_path)
    if info_data:
        input_obj = {
            "type": "http",
            "method": info_data["method"],
        }
        if info_data.get("path_params"):
            input_obj["pathParams"] = info_data["path_params"]
        if info_data.get("query"):
            input_obj["query"] = info_data["query"]
        if info_data.get("body"):
            input_obj["body"] = info_data["body"]
            input_obj["bodyType"] = "json"

        base["info"] = {
            "input": input_obj,
            "output": {
                "type": "json",
                "example": info_data.get("output_example", {}),
            },
            "routeTemplate": info_data["route"],
        }
        base["schema"] = _build_bazaar_schema(info_data)
    return base

@app.middleware("http")
async def enrich_402_bazaar(request, call_next):
    response = await call_next(request)
    # Security headers on all responses
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https:;"
    response.headers["X-RateLimit-Limit"] = "100"
    response.headers["X-RateLimit-Window"] = "60s"

    # Enrich 402 Payment Required responses with Bazaar discovery data
    if response.status_code == 402:
        # Get the payment-required header
        pr_header = response.headers.get("payment-required", "")
        if pr_header:
            try:
                import base64 as _b64
                import json as _json
                # Decode the base64 payment-required payload
                try:
                    decoded = _b64.b64decode(pr_header).decode()
                except Exception:
                    decoded = pr_header  # might already be raw JSON

                payload = _json.loads(decoded)

                # Fix resource URL: http -> https
                resource = payload.get("resource", {})
                if "url" in resource and resource["url"].startswith("http://"):
                    resource["url"] = resource["url"].replace("http://", "https://", 1)

                # Add serviceName and tags to resource (required by Bazaar indexers)
                resource["serviceName"] = "AgentServices"
                resource["tags"] = _BAZAAR_TAGS
                payload["resource"] = resource

                # Add extensions.bazaar to each accept entry
                route_path = resource.get("url", "")
                if "agentservices.to" in route_path:
                    route_path = route_path.split("agentservices.to", 1)[-1]
                elif "aiservices.to" in route_path:
                    route_path = route_path.split("aiservices.to", 1)[-1]
                route_desc = resource.get("description", "AgentServices API")

                bazaar_ext = _build_bazaar_extension(route_path, route_desc)

                for accept in payload.get("accepts", []):
                    # Fix payTo: ensure 0x prefix
                    pay_to = accept.get("payTo", "")
                    if pay_to and not pay_to.startswith("0x"):
                        accept["payTo"] = "0x" + pay_to

                    # Add bazaar extension with full discovery info
                    if "extensions" not in accept:
                        accept["extensions"] = {}
                    accept["extensions"]["bazaar"] = bazaar_ext

                payload.setdefault("extensions", {})["bazaar"] = bazaar_ext

                # Re-encode and update header
                updated_json = _json.dumps(payload, separators=(',', ':'))
                updated_b64 = _b64.b64encode(updated_json.encode()).decode()
                response.headers["payment-required"] = updated_b64

            except Exception as e:
                # Don't break the response if enrichment fails
                print(f"[bazaar-enrich] Warning: failed to enrich 402: {e}", flush=True)

    return response

# --- x402 Payment Protocol (Base Mainnet) ---
# Payment receiver is intentionally separated from WALLET_ADDRESS so an agent
# consumer wallet cannot accidentally become the API revenue wallet in prod.
X402_WALLET = os.environ.get("X402_PAY_TO", os.environ.get("X402_WALLET_ADDRESS", AISERVICES_PAY_TO))
X402_BASE_NETWORK = "eip155:8453"
X402_BSC_NETWORK = "eip155:56"
X402_SVM_NETWORK = "solana:5eychk4D"  # Solana mainnet
X402_FACILITATOR_URL = os.environ.get("X402_FACILITATOR_URL", "https://api.cdp.coinbase.com/platform/v2/x402")

# Multi-chain: Dexter facilitator (x402.dexter.cash) supports Base + BSC + more.
# CDP facilitator supports Base + Solana. We detect and register accordingly.
X402_IS_MULTICHAIN = any(d in X402_FACILITATOR_URL.lower() for d in ("dexter", "infra402", "aeon"))

# Build network list: Always Base, add Solana (CDP supports it), add BSC if multichain facilitator
X402_NETWORKS = [X402_BASE_NETWORK, X402_SVM_NETWORK] + ([X402_BSC_NETWORK] if X402_IS_MULTICHAIN else [])
X402_NETWORK_LABEL = "Base + Solana" + (" + BSC" if X402_IS_MULTICHAIN else "")

X402_ENABLED = False
X402_ERROR = "Not initialized"
try:
    from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption, CreateHeadersAuthProvider
    from x402.http.middleware.fastapi import PaymentMiddlewareASGI, FastAPIAdapter
    from x402.http.types import RouteConfig

    # The upstream FastAPI adapter defaults get_body() to None. Expose the
    # body captured by DynamicBodyMiddleware to DynamicPrice callbacks.
    FastAPIAdapter.get_body = lambda self: self._request.scope.get("state", {}).get("dynamic_body")
    from x402.mechanisms.evm.exact import ExactEvmServerScheme
    from x402.server import x402ResourceServer
    from x402.extensions.bazaar import bazaar_resource_server_extension

    # Build facilitator — CDP needs JWT auth headers, others (Dexter) are open
    facilitator_config_kwargs = {"url": X402_FACILITATOR_URL}
    if not X402_IS_MULTICHAIN:
        from x402_payment import base_supported_response, cdp_auth_available, create_cdp_auth_headers, CDP_FACILITATOR_URL
        facilitator_config_kwargs["url"] = CDP_FACILITATOR_URL
        facilitator_config_kwargs["auth_provider"] = CreateHeadersAuthProvider(create_cdp_auth_headers)

    # CDP Bazaar indexing fix (x402-foundation/x402#2832):
    # CDP facilitator /verify rejects payloads with resource/extensions.
    # Subclass HTTPFacilitatorClient to strip those fields before POST.
    # This restores CDP Bazaar indexing and x402scan marketplace visibility.
    import httpx

    class CDPFixedFacilitatorClient(HTTPFacilitatorClient):
        """HTTPFacilitatorClient that strips resource/extensions from paymentPayload
        before sending to CDP /verify — fixes x402-foundation/x402#2832."""

        def get_supported(self):
            # Unpaid 402 challenges only need supported kinds during initialize().
            # On Vercel, CDP keys are often unset; verify/settle still require them.
            if not X402_IS_MULTICHAIN and not cdp_auth_available():
                return base_supported_response()
            return super().get_supported()

        async def verify(self, payment_payload, payment_requirements):
            payload_dict = payment_payload.model_dump(by_alias=True, exclude_none=True) if hasattr(payment_payload, 'model_dump') else dict(payment_payload)
            payload_dict.pop("resource", None)
            payload_dict.pop("extensions", None)
            if hasattr(payment_payload, 'model_validate'):
                cleaned = type(payment_payload).model_validate(payload_dict)
            else:
                cleaned = payload_dict
            return await super().verify(cleaned, payment_requirements)

        async def settle(self, payment_payload, payment_requirements):
            payload_dict = payment_payload.model_dump(by_alias=True, exclude_none=True) if hasattr(payment_payload, 'model_dump') else dict(payment_payload)
            payload_dict.pop("resource", None)
            payload_dict.pop("extensions", None)
            if hasattr(payment_payload, 'model_validate'):
                cleaned = type(payment_payload).model_validate(payload_dict)
            else:
                cleaned = payload_dict
            return await super().settle(cleaned, payment_requirements)

    facilitator = CDPFixedFacilitatorClient(FacilitatorConfig(**facilitator_config_kwargs))
    payment_server = x402ResourceServer(facilitator)
    # Register EVM networks (Base, BSC)
    payment_server.register(X402_BASE_NETWORK, ExactEvmServerScheme())
    if X402_IS_MULTICHAIN:
        payment_server.register(X402_BSC_NETWORK, ExactEvmServerScheme())
    # Register Solana (SVM) — CDP facilitator supports Solana mainnet
    try:
        from x402.mechanisms.svm.exact import ExactSvmServerScheme
        payment_server.register(X402_SVM_NETWORK, ExactSvmServerScheme())
        print(f"[x402] Solana (SVM) support registered on {X402_SVM_NETWORK}", flush=True)
    except Exception as svm_err:
        print(f"[x402] WARNING: SVM scheme registration failed: {svm_err}", flush=True)
        X402_NETWORKS = [n for n in X402_NETWORKS if n != X402_SVM_NETWORK]
        X402_NETWORK_LABEL = "Base" + (" + BSC" if X402_IS_MULTICHAIN else "")
    payment_server.register_extension(bazaar_resource_server_extension)

    def _payment_options(wallet: str, price: str) -> list:
        """Generate PaymentOption for every supported network (multi-chain)."""
        options = []
        for net in X402_NETWORKS:
            if net.startswith("solana:"):
                # Solana needs a separate SPL wallet address
                svm_wallet = os.environ.get("X402_SVM_PAY_TO", "")
                if svm_wallet:
                    options.append(PaymentOption(scheme="exact", pay_to=svm_wallet, price=price, network=net))
            else:
                options.append(PaymentOption(scheme="exact", pay_to=wallet, price=price, network=net))
        return options

    payment_routes = {
        "POST /v1/disputes": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.05"),
            mime_type="application/json",
            description="Submit a dispute for policy-driven ruling (AgentCourt engine)",
        ),
        "GET /v1/indicators/*": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="Technical indicators: RSI, Bollinger Bands, ATR, Support/Resistance",
        ),
        "GET /v1/yields": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="Top DeFi yield pools by TVL",
        ),
        "GET /v1/metadata": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.01"),
            mime_type="application/json",
            description="URL metadata extraction and unfurling",
        ),
        "GET /v1/search": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.01"),
            mime_type="application/json",
            description="AI-powered web search with structured results",
        ),
        "POST /v1/marketing/sentiment": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="AI brand sentiment analysis across platforms",
        ),
        "POST /v1/marketing/trends": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="Industry trend detection with velocity scores",
        ),
        "POST /v1/marketing/competitors": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.05"),
            mime_type="application/json",
            description="Competitive intelligence — keywords, channels, strategy",
        ),
        "POST /v1/marketing/content-gaps": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.04"),
            mime_type="application/json",
            description="SEO content gap analysis",
        ),
        "POST /v1/marketing/ad-copy": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.05"),
            mime_type="application/json",
            description="AI ad copy generator for Google/Meta/TikTok/Taboola",
        ),
        "GET /v1/whales": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="Large whale transactions on BTC and ETH chains",
        ),
        "GET /v1/exchange-flows": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="CEX reserve flows and 24h changes",
        ),
        "GET /v1/correlation": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="30-day cross-asset correlation matrix",
        ),
        "GET /v1/defi-tvl": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="DeFi protocol TVL rankings from DeFi Llama",
        ),
        "GET /v1/stablecoin-flows": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="Stablecoin market caps and supply data",
        ),
        "GET /v1/github-velocity": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="GitHub crypto repo velocity scores",
        ),
        "GET /v1/macro": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="Macro economic and crypto indicators",
        ),
        # --- Inference Gateway (dynamic pricing: provider cost + 5%) ---
        "POST /v1/inference": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="LLM inference — dynamic pricing (provider cost + 5%, floor $0.003)",
        ),
        "POST /v1/complete": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="Quick text completion — dynamic pricing",
        ),
        # --- NEW: Synthesis Endpoints ---
        "GET /v1/token-risk/*": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="Token risk scoring — volatility, liquidity, market cap analysis",
        ),
        "GET /v1/signals/*": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.04"),
            mime_type="application/json",
            description="Crypto buy/sell signals synthesized from technical indicators",
        ),
        "GET /v1/hn-sentiment": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="Hacker News tech sentiment analysis",
        ),
        "GET /v1/npm-stats/*": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="NPM package download statistics and trend analysis",
        ),
        "GET /v1/github-trending": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="GitHub trending repositories",
        ),
        "GET /v1/yield-comparison": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="DeFi yield comparison with risk-adjusted analysis",
        ),
        # --- NEW: Traditional Finance (gap fillers) ---
        "GET /v1/stocks/*": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="Real-time stock quotes from Yahoo Finance",
        ),
        "GET /v1/stocks/*/history": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="Historical OHLCV stock data",
        ),
        "GET /v1/sec/*": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="SEC filings parser — 10-K, 10-Q, 8-K, Form 4 from EDGAR",
        ),
        "GET /v1/commodities": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="Commodity prices — oil, gold, silver, copper, wheat, more",
        ),
        "GET /v1/economic": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="US economic indicators — CPI, GDP, unemployment, Fed rate",
        ),
        "GET /v1/fx": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.003"),
            mime_type="application/json",
            description="Real-time FX/forex rates for 30+ currencies",
        ),
        "GET /v1/fx-rates": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.003"),
            mime_type="application/json",
            description="Real-time FX/forex rates for 30+ currencies (alias for /v1/fx)",
        ),
        "GET /v1/gov/us/ca/entity": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="California business entity status lookup by name or entity number",
        ),
        # --- NEW: Utility (gap fillers) ---
        "GET /v1/extract": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.002"),
            mime_type="application/json",
            description="Web content extraction — clean text from any URL",
        ),
        "GET /v1/security/*": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="Package security scan — check PyPI/npm for vulnerabilities",
        ),
        "GET /v1/seo/keywords": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.01"),
            mime_type="application/json",
            description="SEO keyword research — volume estimates and competition",
        ),
        "GET /v1/backlinks": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="Backlink list — discovered external pages linking to the target domain",
        ),
        # --- NEW: Deep Research (flagship bundled endpoint) ---
        "GET /v1/research": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.05"),
            mime_type="application/json",
            description="Deep research — search + extract + synthesize in one call",
        ),
        # --- NEW: Portfolio Intelligence (bundled endpoint) ---
        "GET /v1/portfolio": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.10"),
            mime_type="application/json",
            description="Portfolio intelligence — price + signal + risk + sentiment in one call",
        ),
        # --- NEW: DeFi Strategy Report (high-value bundled) ---
        "GET /v1/defi-strategy": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.25"),
            mime_type="application/json",
            description="DeFi strategy report — yields + TVL + comparison + risk in one call",
        ),
        # --- NEW: Market Pulse (rapid snapshot) ---
        "GET /v1/market-pulse": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.05"),
            mime_type="application/json",
            description="Market pulse — sentiment + trending + news + social + whales + global in one call",
        ),
        "GET /v1/onchain-overview": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.15"),
            mime_type="application/json",
            description="On-chain overview — whales + exchange flows + stablecoin flows + correlation + DeFi TVL",
        ),
        "GET /v1/arbitrage": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.08"),
            mime_type="application/json",
            description="Cross-DEX arbitrage scanner — price discrepancies, gas-adjusted profitability, slippage modeling",
        ),
        # --- Agent Memory (retention hook) ---
        "POST /v1/memory/*": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.01"),
            mime_type="application/json",
            description="Store agent memory — persistent wallet-keyed KV",
        ),
        "GET /v1/memory/*": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.01"),
            mime_type="application/json",
            description="Retrieve agent memory",
        ),
        "DELETE /v1/memory/*": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.01"),
            mime_type="application/json",
            description="Delete agent memory entry",
        ),
        "POST /v1/memory/search": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.02"),
            mime_type="application/json",
            description="Semantic search across agent memory",
        ),
        # --- Skill Packs (bundled intelligence) ---
        "POST /v1/skills/crypto-dossier": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.10"),
            mime_type="application/json",
            description="Crypto dossier — price + indicators + risk + signal + fear/greed + whales in one call",
        ),
        "POST /v1/skills/stock-dossier": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.05"),
            mime_type="application/json",
            description="Stock dossier — quote + FX rates + sentiment in one call",
        ),
        "GET /v1/skills/market-overview": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.05"),
            mime_type="application/json",
            description="Market pulse — fear/greed + BTC signal + whales + regime classification",
        ),
        # --- Media Gateway (image, TTS, multi-model) ---
        "POST /v1/images/generations": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.05"),
            mime_type="application/json",
            description="AI image generation via gpt-image-2",
        ),
        "POST /v1/audio/speech": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.05"),
            mime_type="application/json",
            description="Text-to-speech via gpt-audio",
        ),
        "POST /v1/chat/completions": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.03"),
            mime_type="application/json",
            description="Chat completions — dynamic pricing (provider cost + 5%, floor $0.003). 400+ models. Use model=auto for smart routing.",
        ),
        # --- Voice Gateway (phone, calls) ---
        "POST /v1/calls": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.54"),
            mime_type="application/json",
            description="AI voice call — outbound phone call with text-to-speech",
        ),
        "GET /v1/lookup/*": RouteConfig(
            accepts=_payment_options(X402_WALLET, "$0.05"),
            mime_type="application/json",
            description="Phone number lookup — carrier, type, fraud risk",
        ),
    }

    # DynamicPrice is evaluated by x402 with the request context before 402.
    from x402.http.types import HTTPRequestContext
    def _dynamic_chat_price(context):
        # Never undercharge if a framework adapter cannot expose the body.
        # The conservative fallback is an authorization ceiling, not a margin
        # claim; the normal path computes provider cost + 5% from live rates.
        body = context.adapter.get_body()
        if not isinstance(body, dict) or not body:
            return "$0.25"
        model = body.get("model") or "auto"
        messages = body.get("messages", [])
        max_tokens = min(int(body.get("max_tokens", 1000) or 1000), 4096)
        if model == "auto":
            from inference_gateway import _route_model
            model = _route_model("auto", messages, body.get("profile", "auto"))
        return calc_dynamic_price(model, messages, max_tokens)
    for route_key in ("POST /v1/chat/completions", "POST /v1/inference", "POST /v1/complete"):
        route = payment_routes.get(route_key)
        if route:
            for option in route.accepts:
                option.price = _dynamic_chat_price

    # Use function middleware so request body can be parsed by the dynamic price hook.
    from x402.http.middleware.fastapi import payment_middleware
    app.middleware("http")(payment_middleware(payment_routes, payment_server))
    # Register after x402 so Starlette executes it before x402 on the request path.
    app.add_middleware(DynamicBodyMiddleware)
    # Must wrap x402 so the request body is priced before the payment challenge.
    print(f"[x402] Payment middleware enabled on {X402_NETWORK_LABEL} — disputes ($0.05), indicators/yields/correlation ($0.02–$0.03), metadata/search ($0.01), marketing ($0.03–$0.05), on-chain data ($0.02–$0.03)", flush=True)
    X402_ENABLED = True
    X402_ERROR = None

    # CRITICAL: Bazaar discovery enrichment middleware — must be added AFTER
    # PaymentMiddlewareASGI so it's the outermost layer and can intercept 402
    # responses from the x402 middleware. Without this, CDP Bazaar indexers
    # never see extensions.bazaar in the live 402 and resources stay stuck
    # in "processing" — never appearing on agentic.market.
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import Response as StarletteResponse
    import base64 as _b64_enrich
    import json as _json_enrich

    _ENRICH_TAGS = ["data", "crypto", "defi", "search", "inference", "marketing-intelligence", "onchain", "analytics"]

    class BazaarEnrichmentMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            if response.status_code == 402:
                pr_header = response.headers.get("payment-required", "")
                if pr_header:
                    try:
                        # Try base64 decode first, then raw JSON
                        try:
                            decoded = _b64_enrich.b64decode(pr_header).decode()
                        except Exception:
                            decoded = pr_header

                        payload = _json_enrich.loads(decoded)

                        # Fix resource URL: http -> https
                        resource = payload.get("resource", {})
                        if "url" in resource and resource["url"].startswith("http://"):
                            resource["url"] = resource["url"].replace("http://", "https://", 1)

                        # Add serviceName and tags to resource (Bazaar indexer requirement)
                        resource["serviceName"] = "AgentServices"
                        resource["tags"] = _ENRICH_TAGS
                        payload["resource"] = resource

                        route_desc = resource.get("description", "AgentServices API")
                        route_path = resource.get("url", "")
                        if "agentservices.to" in route_path:
                            route_path = route_path.split("agentservices.to", 1)[-1]
                        elif "aiservices.to" in route_path:
                            route_path = route_path.split("aiservices.to", 1)[-1]

                        bazaar_ext = _build_bazaar_extension(route_path, route_desc)

                        # Enrich accepts with bazaar extension + fix payTo
                        for accept in payload.get("accepts", []):
                            # Fix payTo: ensure 0x prefix
                            pay_to = accept.get("payTo", "")
                            if pay_to and not pay_to.startswith("0x"):
                                accept["payTo"] = "0x" + pay_to

                            # Add bazaar extension with full discovery info
                            if "extensions" not in accept:
                                accept["extensions"] = {}
                            accept["extensions"]["bazaar"] = bazaar_ext

                        payload.setdefault("extensions", {})["bazaar"] = bazaar_ext

                        # Re-encode and update header
                        updated_json = _json_enrich.dumps(payload, separators=(',', ':'))
                        updated_b64 = _b64_enrich.b64encode(updated_json.encode()).decode()
                        response.headers["payment-required"] = updated_b64

                        print(f"[bazaar-enrich] Enriched 402 for {resource.get('url', 'unknown')}", flush=True)

                    except Exception as e:
                        print(f"[bazaar-enrich] Warning: failed to enrich 402: {e}", flush=True)

            return response

    app.add_middleware(BazaarEnrichmentMiddleware)
    print("[bazaar-enrich] Bazaar discovery enrichment middleware enabled", flush=True)

except ImportError as e:
    print(f"[x402] NOT installed — running in free mode. Error: {e}", flush=True)
    X402_ENABLED = False
    X402_ERROR = f"ImportError: {e}"
except Exception as e:
    import traceback
    print(f"[x402] Failed to initialize — running in free mode. Error: {e}", flush=True)
    traceback.print_exc()
    X402_ENABLED = False
    X402_ERROR = f"{type(e).__name__}: {e}"

# --- MCP Remote Transport ---
app.include_router(mcp_router)
print(f"[mcp] Remote MCP endpoint mounted at /mcp — 21 tools available", flush=True)


# --- Market Data ---

@app.get("/v1/price/{symbol}", tags=["Market Data"])
async def crypto_price(symbol: str):
    """Current crypto price (FREE)"""
    return get_price(symbol)

@app.get("/v1/prices", tags=["Market Data"])
async def crypto_prices(symbols: str = "BTC,ETH,SOL,XRP"):
    """Batch crypto prices (FREE)"""
    return get_multi_price(symbols.split(","))

@app.get("/v1/indicators/{symbol}", tags=["Market Data"])
async def crypto_indicators(symbol: str):
    """Technical indicators: RSI, BB, ATR, S/R ($0.02)"""
    return get_indicators(symbol)

@app.get("/v1/yields", tags=["Market Data"],
         response_model=dict,
         responses={
             200: {
                 "content": {
                     "application/json": {
                         "schema": {
                             "type": "object",
                             "properties": {
                                 "pools": {
                                     "type": "array",
                                     "items": {
                                         "type": "object",
                                         "properties": {
                                             "protocol": {"type": "string"},
                                             "pool": {"type": "string"},
                                             "apy": {"type": "number"},
                                             "tvl_usd": {"type": "number"},
                                             "chain": {"type": "string"},
                                         }
                                     }
                                 }
                             }
                         }
                     }
                 },
                 "description": "Top DeFi yield pools ranked by TVL"
             },
             402: {"description": "Payment required — $0.02 USDC on Base"}
         },
         summary="Top DeFi Yield Pools",
         description="Returns top DeFi yield farming pools ranked by TVL across major protocols. Costs $0.02 USDC via x402.")
async def defi_yields(
    limit: int = 20,
    chain: str = "all"
):
    """Top DeFi yield pools by TVL ($0.02)"""
    return get_defi_yields()

@app.get("/v1/fear-greed", tags=["Market Data"])
async def fear_greed():
    """Crypto Fear & Greed Index (FREE)"""
    return get_fear_greed()


# --- Geolocation ---

@app.get("/v1/geo/{ip}", tags=["Location"])
async def ip_geo(ip: str):
    """IP geolocation lookup (FREE)"""
    return get_ip_geo(ip)


# --- Web Data ---

@app.get("/v1/metadata", tags=["Web Data"])
async def url_metadata(url: str):
    """URL metadata extraction and unfurling ($0.01)"""
    return get_url_metadata(url)


# --- Dispute Resolution (AgentCourt engine) ---

class DisputeRequest(BaseModel):
    policy: str = Field(description="Policy template name (e.g. freelance-delivery)")
    claimant: str = Field(description="Plaintiff address or agent ID")
    respondent: str = Field(description="Respondent address or agent ID")
    claim: str = Field("", description="What happened")
    desired_remedy: str = Field("", description="What the claimant wants")
    evidence: list = Field(default_factory=list, description="Evidence items")

@app.post("/v1/disputes", tags=["Dispute Resolution"])
async def resolve_dispute(req: DisputeRequest):
    """Submit a dispute for policy-driven ruling ($0.05 via x402)"""
    dispute_dict = {
        "claimant": req.claimant,
        "respondent": req.respondent,
        "claim": req.claim,
        "desired_remedy": req.desired_remedy,
    }
    ruling = evaluate_dispute(
        dispute=dispute_dict,
        evidence=req.evidence,
        policy_name=req.policy,
    )
    return ruling

@app.get("/v1/policies", tags=["Dispute Resolution"])
async def get_policies():
    """List available dispute policy templates (FREE)"""
    return list_policies()


# --- Web Search ---

@app.get("/v1/search", tags=["Search"],
         summary="Web Search",
         description="AI-powered web search. Returns structured results with titles, URLs, and snippets. Uses Exa if API key available, otherwise DuckDuckGo.")
async def search_web(q: str, num: int = 5):
    """Web search — structured results ($0.01 via x402)"""
    return web_search(q, num)


# --- DEX / Trading ---

@app.get("/v1/swap/quote", tags=["DEX"],
         summary="DEX Swap Quote",
         description="Get a swap quote from 0x API across Ethereum, Base, Polygon, Arbitrum, Optimism, BSC.")
async def swap_quote(
    chain: str = "ethereum",
    sellToken: str = "WETH",
    buyToken: str = "USDC",
    sellAmount: str = "1000000000000000000",
):
    """Get DEX swap quote from 0x API (FREE)"""
    return get_swap_quote(chain, sellToken, buyToken, sell_amount=sellAmount)


@app.get("/v1/trending", tags=["Market Data"],
         summary="Trending Tokens",
         description="Get trending tokens and coins being searched right now on CoinGecko.")
async def trending_tokens():
    """Trending tokens — most searched right now (FREE)"""
    return get_trending_tokens()


@app.get("/v1/gas", tags=["Market Data"],
         summary="Gas Tracker",
         description="Current gas prices for Ethereum (slow, standard, fast) in Gwei.")
async def gas_tracker():
    """Current gas prices (FREE)"""
    return get_gas_tracker()


# --- Prediction Markets ---

@app.get("/v1/predictions", tags=["Prediction Markets"],
         summary="Prediction Markets",
         description="Get active prediction markets from Polymarket ranked by 24h volume.")
async def prediction_markets(limit: int = 20):
    """Active prediction markets from Polymarket (FREE)"""
    return get_polymarket_markets(limit=limit)


@app.get("/v1/predictions/{slug}", tags=["Prediction Markets"],
         summary="Prediction Market Details",
         description="Get details for a specific Polymarket prediction market.")
async def prediction_market_detail(slug: str):
    """Specific prediction market details (FREE)"""
    return get_polymarket_market(slug)


# --- News & Social ---

@app.get("/v1/news", tags=["News"],
         summary="Crypto News",
         description="Latest crypto and blockchain news from multiple sources.")
async def crypto_news(limit: int = 20):
    """Latest crypto news (FREE)"""
    return get_crypto_news(limit=limit)


@app.get("/v1/social", tags=["News"],
         summary="Social Trending",
         description="Trending crypto topics: coins, categories, and NFTs being discussed.")
async def social_trending():
    """Social trending — coins, categories, NFTs (FREE)"""
    return get_social_trending()


@app.get("/v1/global", tags=["Market Data"],
         summary="Global Market Stats",
         description="Global crypto market data: total market cap, volume, BTC dominance.")
async def global_market():
    """Global market stats (FREE)"""
    return get_global_market()


# --- Marketing Intelligence (AI-Powered) ---

@app.post("/v1/marketing/sentiment", tags=["Marketing Intelligence"],
          summary="Brand Sentiment Analysis",
          description="AI-powered brand sentiment analysis across platforms. Uses GPT-4o-mini for real-time analysis.")
async def marketing_sentiment(req: SentimentRequest):
    """Brand sentiment analysis (FREE during beta)"""
    return analyze_sentiment(req.brand, req.platforms)

@app.post("/v1/marketing/trends", tags=["Marketing Intelligence"],
          summary="Industry Trend Detection",
          description="Detect trending marketing topics in any industry with velocity scores and content recommendations.")
async def marketing_trends(req: TrendRequest):
    """Industry trend detection (FREE during beta)"""
    return detect_trends(req.industry, req.limit)

@app.post("/v1/marketing/competitors", tags=["Marketing Intelligence"],
          summary="Competitive Intelligence",
          description="AI-powered competitor analysis: keywords, channels, content strategy, and actionable recommendations.")
async def marketing_competitors(req: CompetitorRequest):
    """Competitive intelligence (FREE during beta)"""
    return analyze_competitors(req.competitor_url, req.your_url)

@app.post("/v1/marketing/content-gaps", tags=["Marketing Intelligence"],
          summary="Content Gap Analysis",
          description="Find SEO content gaps between you and competitors. Includes keyword opportunities with difficulty scores.")
async def marketing_content_gaps(req: ContentGapRequest):
    """Content gap analysis (FREE during beta)"""
    return find_content_gaps(req.your_domain, req.competitor_domains)

@app.post("/v1/marketing/ad-copy", tags=["Marketing Intelligence"],
          summary="AI Ad Copy Generator",
          description="Generate ad copy variations for Google, Meta, TikTok, or Taboola. Platform-specific constraints and tone control.")
async def marketing_ad_copy(req: AdCopyRequest):
    """AI ad copy generation (FREE during beta)"""
    return generate_ad_copy(req.product, req.platform, req.tone, req.count)



# --- On-Chain & Advanced Data (Gap Fillers) ---

@app.get("/v1/whales", tags=["On-Chain Data"],
         summary="Large Transaction Tracking",
         description="Whale transactions: large BTC (>=10 BTC) and ETH movements from public blockchain APIs. ($0.02)")
async def whale_tracking(limit: int = 50, min_btc: float = 10.0):
    """Large on-chain whale transactions ($0.02)"""
    return get_whales()

@app.get("/v1/exchange-flows", tags=["On-Chain Data"],
         summary="CEX Reserve Flows",
         description="Centralized exchange reserves and 24h changes from DeFi Llama transparency data. ($0.02)")
async def exchange_flows(limit: int = 20):
    """CEX inflow/outflow tracking ($0.02)"""
    return get_exchange_flows()

@app.get("/v1/correlation", tags=["Market Data"],
         summary="Cross-Asset Correlation Matrix",
         description="30-day Pearson correlations across top crypto assets (BTC, ETH, SOL, XRP, BNB, etc.). ($0.03)")
async def correlation_matrix(days: int = 30):
    """Cross-asset correlation matrix ($0.03)"""
    return get_correlation_matrix()

@app.get("/v1/defi-tvl", tags=["DeFi"],
         summary="DeFi Protocol TVL Rankings",
         description="Top DeFi protocols ranked by Total Value Locked from DeFi Llama. ($0.02)")
async def defi_tvl(limit: int = 20, chain: str = "all"):
    """DeFi protocol TVL rankings ($0.02)"""
    return get_defi_tvl(limit, chain)

@app.get("/v1/stablecoin-flows", tags=["On-Chain Data"],
         summary="Stablecoin Market Caps & Flows",
         description="Top stablecoins by market cap with supply data from DeFi Llama. ($0.02)")
async def stablecoin_flows(limit: int = 20):
    """Stablecoin supply and flows ($0.02)"""
    return get_stablecoin_flows()

@app.get("/v1/github-velocity", tags=["Developer Activity"],
         summary="GitHub Repo Velocity Scores",
         description="Trending crypto/web3 GitHub repos with computed velocity scores. ($0.02)")
async def github_velocity(language: str = "", limit: int = 15):
    """GitHub repo activity with velocity scoring ($0.02)"""
    return get_github_velocity(language, limit)

@app.get("/v1/agent-context", tags=["AI Agent Tools"],
         summary="Paste-Ready Agent Context",
         description="Composed multi-source market context in a single paste-ready payload for LLM system prompts. (FREE)")
async def agent_context():
    """Composed context for AI agents (FREE)"""
    return get_agent_context()

@app.get("/v1/macro", tags=["Market Data"],
         summary="Macro Economic Indicators",
         description="Crypto-macro indicators: global market cap, dominance, derivatives data. ($0.02)")
async def macro_indicators(currency: str = "usd"):
    """Macro economic indicators ($0.02)"""
    return get_macro()


# --- Health & Discovery ---

_landing_html = None
def _get_landing():
    global _landing_html
    if _landing_html is None:
        landing_path = Path(__file__).parent / "landing.html"
        if landing_path.exists():
            _landing_html = landing_path.read_text()
        else:
            _landing_html = "<h1>AgentServices</h1>"
    return _landing_html


def _live_capability_summary() -> dict:
    """Generate discovery facts from the registered FastAPI schema, never stale copy."""
    schema = app.openapi()
    paths = schema.get("paths", {})
    identity = [p for p in paths if p.startswith("/v1/erc8004/") or p.startswith("/v1/agents/") or p.startswith("/v1/evidence/") or p.startswith("/v1/claims/")]
    return {"path_count": len(paths), "identity_evidence_paths": sorted(identity), "openapi": "/openapi.json", "generated": "runtime"}


def _get_llms_full_markdown():
    """Return a concise markdown version of the landing page for content negotiation."""
    live = _live_capability_summary()
    return f"""# AgentServices — APIs for AI Agents

AgentServices exposes {live['path_count']} registered API routes. Data, search, market intelligence, DeFi strategy, cross-DEX arbitrage, AI inference, ERC-8004 agent discovery, reputation, and evidence verification. Paid routes use x402 (USDC on Base).

## Live capability discovery

The capability list is generated from the deployed OpenAPI schema, not hardcoded marketing copy:
- OpenAPI: https://agentservices.to/openapi.json
- Catalog search: https://agentservices.to/v1/catalog/search
- Identity and evidence routes: {', '.join(live['identity_evidence_paths'])}
"""

@app.get("/")
async def root(request: Request):
    """Route based on domain: agentservices.to serves website HTML, all paths serve API."""
    # Markdown content negotiation
    accept = request.headers.get("accept", "")
    if "text/markdown" in accept or "text/x-markdown" in accept:
        from starlette.responses import PlainTextResponse
        return PlainTextResponse(
            content=_get_llms_full_markdown(),
            media_type="text/markdown"
        )
    host = request.headers.get("host", "").split(":")[0].lower()
    if host.startswith("api."):
        return {
            "name": "AgentServices",
            "tagline": "Paid APIs for AI agents — data, inference, and market intelligence",
            "version": "5.3.0",
            "payment": "x402 / USDC on Base",
            "wallet": X402_WALLET,
            "services": {
                "market_data": {
                    "price": {"endpoint": "GET /v1/price/{symbol}", "price": "free", "desc": "Current crypto price"},
                    "batch_prices": {"endpoint": "GET /v1/prices?symbols=BTC,ETH", "price": "free", "desc": "Batch crypto prices"},
                    "indicators": {"endpoint": "GET /v1/indicators/{symbol}", "price": "$0.02", "desc": "RSI, Bollinger Bands, ATR, Support/Resistance"},
                    "yields": {"endpoint": "GET /v1/yields", "price": "$0.02", "desc": "Top DeFi yield pools by TVL"},
                    "fear_greed": {"endpoint": "GET /v1/fear-greed", "price": "free", "desc": "Crypto Fear & Greed Index"},
                    "global": {"endpoint": "GET /v1/global", "price": "free", "desc": "Global market cap, volume, BTC dominance"},
                    "trending": {"endpoint": "GET /v1/trending", "price": "free", "desc": "Trending tokens right now"},
                    "gas": {"endpoint": "GET /v1/gas", "price": "free", "desc": "Current ETH gas prices"},
                },
                "search": {
                    "web_search": {"endpoint": "GET /v1/search?q=...", "price": "$0.01", "desc": "AI-powered web search"},
                },
                "dex": {
                    "swap_quote": {"endpoint": "GET /v1/swap/quote", "price": "free", "desc": "DEX swap quote (0x API, 6 chains)"},
                },
                "prediction_markets": {
                    "markets": {"endpoint": "GET /v1/predictions", "price": "free", "desc": "Active Polymarket prediction markets"},
                    "detail": {"endpoint": "GET /v1/predictions/{slug}", "price": "free", "desc": "Specific market details"},
                },
                "news_social": {
                    "news": {"endpoint": "GET /v1/news", "price": "free", "desc": "Latest crypto news"},
                    "social_trending": {"endpoint": "GET /v1/social", "price": "free", "desc": "Trending coins, categories, NFTs"},
                },
                "dispute_resolution": {
                    "file_dispute": {"endpoint": "POST /v1/disputes", "price": "$0.05", "desc": "Submit dispute for policy-driven ruling (AgentCourt engine)"},
                    "policies": {"endpoint": "GET /v1/policies", "price": "free", "desc": "List dispute policy templates"},
                },
            },
            "live": True,
        }
    return HTMLResponse(content=_get_landing())


@app.get("/v1/catalog/search", tags=["Discovery"])
async def catalog_search(query: str = "", tag: list[str] | None = Query(default=None), limit: int = 25):
    """Find AgentServices capabilities by task, not by vendor or route."""
    return {
        "query": query,
        "tools": search_catalog(query, tag, limit),
        "total": len(search_catalog(query, tag, limit)),
        "next": "Use GET /v1/catalog/tools/{id} for the call contract and quote.",
    }


@app.get("/v1/catalog/tools/{tool_id:path}", tags=["Discovery"])
async def catalog_tool(tool_id: str):
    """Return a single task-oriented tool contract and its current quote."""
    tool = get_tool(tool_id)
    if not tool:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Unknown catalog tool")
    return tool


@app.get("/v1/catalog/platforms", tags=["Discovery"])
async def catalog_platforms():
    """Return catalog metadata without overstating external provider coverage."""
    tools = search_catalog(limit=100)
    return {
        "name": "AgentServices catalog",
        "tool_count": len(tools),
        "provider_count": 1,
        "providers": [{"id": "agentservices", "status": "active", "credential_mode": "x402"}],
        "scope": "first-party AgentServices endpoints",
        "tools": tools,
    }


@app.get("/api")
async def api_discovery():
    """API discovery JSON for agents and crawlers."""
    return {
        "name": "AgentServices",
        "tagline": "Paid APIs for AI agents — data, inference, and market intelligence",
        "version": "5.3.0",
        "payment": "x402 / USDC on Base",
        "wallet": X402_WALLET,
        "services": {
            "market_data": {
                "price": {"endpoint": "GET /v1/price/{symbol}", "price": "free", "desc": "Current crypto price"},
                "batch_prices": {"endpoint": "GET /v1/prices?symbols=BTC,ETH", "price": "free", "desc": "Batch crypto prices"},
                "indicators": {"endpoint": "GET /v1/indicators/{symbol}", "price": "$0.02", "desc": "RSI, Bollinger Bands, ATR, Support/Resistance"},
                "yields": {"endpoint": "GET /v1/yields", "price": "$0.02", "desc": "Top DeFi yield pools by TVL"},
                "fear_greed": {"endpoint": "GET /v1/fear-greed", "price": "free", "desc": "Crypto Fear & Greed Index"},
                "global": {"endpoint": "GET /v1/global", "price": "free", "desc": "Global market cap, volume, BTC dominance"},
                "trending": {"endpoint": "GET /v1/trending", "price": "free", "desc": "Trending tokens right now"},
                "gas": {"endpoint": "GET /v1/gas", "price": "free", "desc": "Current ETH gas prices"},
            },
            "search": {
                "web_search": {"endpoint": "GET /v1/search?q=...", "price": "$0.01", "desc": "AI-powered web search"},
                "deep_research": {"endpoint": "GET /v1/research?q=...", "price": "$0.05", "desc": "Search + extract + synthesize in one call"},
                "portfolio_intelligence": {"endpoint": "GET /v1/portfolio?symbol=...", "price": "$0.10", "desc": "Price + signal + risk + sentiment in one call"},
                "defi_strategy": {"endpoint": "GET /v1/defi-strategy?chain=...", "price": "$0.25", "desc": "DeFi yields + TVL + comparison + risk analysis"},
                "market_pulse": {"endpoint": "GET /v1/market-pulse", "price": "$0.05", "desc": "Sentiment + trending + news + whales + global in one call"},
                "onchain_overview": {"endpoint": "GET /v1/onchain-overview", "price": "$0.15", "desc": "Whales + exchange flows + stablecoin flows + correlation + DeFi TVL"},
                "arbitrage_scanner": {"endpoint": "GET /v1/arbitrage?symbols=BTC,ETH,SOL", "price": "$0.08", "desc": "Cross-DEX price discrepancies + gas-adjusted profitability modeling"},
                "liquidation_map": {"endpoint": "GET /v1/liquidation-map?symbols=BTC,ETH,LINK", "price": "$0.12", "desc": "DeFi liquidation heatmap across Aave/Compound/MakerDAO with cascading risk modeling"},
            },
            "dex": {
                "swap_quote": {"endpoint": "GET /v1/swap/quote", "price": "free", "desc": "DEX swap quote (0x API, 6 chains)"},
            },
            "prediction_markets": {
                "markets": {"endpoint": "GET /v1/predictions", "price": "free", "desc": "Active Polymarket prediction markets"},
                "detail": {"endpoint": "GET /v1/predictions/{slug}", "price": "free", "desc": "Specific market details"},
            },
            "news_social": {
                "news": {"endpoint": "GET /v1/news", "price": "free", "desc": "Latest crypto news"},
                "social_trending": {"endpoint": "GET /v1/social", "price": "free", "desc": "Trending coins, categories, NFTs"},
            },
            "dispute_resolution": {
                "file_dispute": {"endpoint": "POST /v1/disputes", "price": "$0.05", "desc": "Submit dispute for policy-driven ruling (AgentCourt engine)"},
                "policies": {"endpoint": "GET /v1/policies", "price": "free", "desc": "List dispute policy templates"},
            },
            "marketing_intelligence": {
                "sentiment": {"endpoint": "POST /v1/marketing/sentiment", "price": "$0.03", "desc": "Brand sentiment analysis (AI-powered)"},
                "trends": {"endpoint": "POST /v1/marketing/trends", "price": "$0.03", "desc": "Industry trend detection"},
                "competitors": {"endpoint": "POST /v1/marketing/competitors", "price": "$0.05", "desc": "Competitive intelligence"},
                "content_gaps": {"endpoint": "POST /v1/marketing/content-gaps", "price": "$0.04", "desc": "SEO content gap analysis"},
                "ad_copy": {"endpoint": "POST /v1/marketing/ad-copy", "price": "$0.05", "desc": "AI ad copy generation"},
            },
            "onchain_data": {
                "whales": {"endpoint": "GET /v1/whales", "price": "$0.02", "desc": "Large whale transactions on BTC/ETH"},
                "exchange_flows": {"endpoint": "GET /v1/exchange-flows", "price": "$0.02", "desc": "CEX reserve flows"},
                "stablecoin_flows": {"endpoint": "GET /v1/stablecoin-flows", "price": "$0.02", "desc": "Stablecoin market caps and supply"},
            },
            "advanced_market_data": {
                "correlation": {"endpoint": "GET /v1/correlation", "price": "$0.03", "desc": "30-day cross-asset correlation matrix"},
                "defi_tvl": {"endpoint": "GET /v1/defi-tvl", "price": "$0.02", "desc": "DeFi protocol TVL rankings"},
                "macro": {"endpoint": "GET /v1/macro", "price": "$0.02", "desc": "Macro economic indicators"},
            },
            "developer_activity": {
                "github_velocity": {"endpoint": "GET /v1/github-velocity", "price": "$0.02", "desc": "GitHub crypto repo velocity scores"},
            },
            "agent_tools": {
                "agent_context": {"endpoint": "GET /v1/agent-context", "price": "free", "desc": "Paste-ready market context for LLMs"},
            },
        },
        "live": True,
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "5.3.0",
        "deploy": {
            "commit": os.environ.get("VERCEL_GIT_COMMIT_SHA"),
            "ref": os.environ.get("VERCEL_GIT_COMMIT_REF"),
            "env": os.environ.get("VERCEL_ENV"),
        },
        "x402_enabled": X402_ENABLED,
        "x402_error": X402_ERROR,
        "x402_networks": X402_NETWORKS,
        "x402_facilitator": X402_FACILITATOR_URL,
        "services": ["crypto_prices", "indicators", "defi_yields", "fear_greed", "geo", "metadata", "search", "swap_quote", "trending", "gas", "predictions", "news", "social_trending", "global", "disputes", "policies", "marketing_sentiment", "marketing_trends", "marketing_competitors", "marketing_content_gaps", "marketing_ad_copy", "whales", "exchange_flows", "correlation", "defi_tvl", "stablecoin_flows", "github_velocity", "agent_context", "macro", "inference", "quick_complete", "token_risk", "crypto_signals", "hn_sentiment", "npm_stats", "github_trending", "yield_comparison", "stock_quote", "stock_history", "sec_filings", "commodities", "economic_indicators", "fx_rates", "web_extract", "package_security", "seo_keywords", "deep_research", "portfolio_intelligence", "defi_strategy", "market_pulse", "onchain_overview", "arbitrage_scanner", "liquidation_map"],
    }


@app.get("/api/health")
async def api_health():
    return await health()


@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import FileResponse
    favicon_path = Path(__file__).parent.parent / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path, media_type="image/x-icon")
    return {"detail": "not found"}, 404


@app.get("/.well-known/ai-plugin.json")
async def ai_plugin():
    return {
        "schema_version": "v1",
        "name_for_model": "agentservices",
        "name_for_human": "AgentServices",
        "description_for_model": "Paid APIs for AI agents. Crypto, DeFi, stocks, FX, research, 37 MCP tools. x402 payments on Base.",
        "description_for_human": "Financial data APIs for AI agents.",
        "auth": {"type": "none"},
        "api": {"type": "openapi", "url": "https://agentservices.to/openapi.json"},
        "logo_url": "https://agentservices.to/favicon.ico",
        "contact_email": "vbkotecha@gmail.com",
        "legal_info_url": "https://agentservices.to/",
    }


@app.get("/skill.md")
async def skill_md():
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        """---
name: agentservices
description: Access paid APIs for AI agents — crypto, DeFi, stocks, research. 37 MCP tools. x402 payments (USDC on Base).
---

# AgentServices — Paid APIs for AI Agents

53 API endpoints (41 paid). Agents pay per-request via x402 (USDC on Base).

## Free Endpoints
- GET /v1/price/{symbol} — Crypto prices
- GET /v1/prices — Batch crypto prices
- GET /v1/fear-greed — Fear & Greed index
- GET /v1/gas — Gas prices
- GET /v1/trending — Trending tokens

## Paid Endpoints (x402)
- GET /v1/indicators/{symbol} ($0.02) — Technical indicators
- GET /v1/yields ($0.02) — DeFi yield pools
- GET /v1/whales ($0.02) — Whale transactions
- GET /v1/portfolio?symbol=BTC ($0.10) — Portfolio intelligence
- GET /v1/market-pulse ($0.05) — Market snapshot
- POST /v1/deep-research ($0.05) — Research brief

## MCP
Connect: https://agentservices.to/mcp (37 tools, Streamable HTTP)

## Base URL
https://agentservices.to
""",
        media_type="text/markdown",
    )


@app.get("/.well-known/x402")
async def x402_manifest():
    """x402 payment manifest for agent discovery."""
    endpoints = [
        {"path": "/v1/price/{symbol}", "method": "GET", "price": "$0.00", "description": "Current crypto price (FREE)"},
        {"path": "/v1/prices", "method": "GET", "price": "$0.00", "description": "Batch crypto prices (FREE)"},
        {"path": "/v1/fear-greed", "method": "GET", "price": "$0.00", "description": "Crypto Fear and Greed Index (FREE)"},
        {"path": "/v1/global", "method": "GET", "price": "$0.00", "description": "Global market cap, volume, dominance (FREE)"},
        {"path": "/v1/trending", "method": "GET", "price": "$0.00", "description": "Trending tokens (FREE)"},
        {"path": "/v1/gas", "method": "GET", "price": "$0.00", "description": "Current ETH gas prices (FREE)"},
        {"path": "/v1/geo/{ip}", "method": "GET", "price": "$0.00", "description": "IP geolocation lookup (FREE)"},
        {"path": "/v1/swap/quote", "method": "GET", "price": "$0.00", "description": "DEX swap quote across 6 chains (FREE)"},
        {"path": "/v1/predictions", "method": "GET", "price": "$0.00", "description": "Active prediction markets (FREE)"},
        {"path": "/v1/news", "method": "GET", "price": "$0.00", "description": "Latest crypto news (FREE)"},
        {"path": "/v1/social", "method": "GET", "price": "$0.00", "description": "Trending coins, categories, NFTs (FREE)"},
        {"path": "/v1/policies", "method": "GET", "price": "$0.00", "description": "List dispute resolution policy templates (FREE)"},
        {"path": "/mcp", "method": "POST", "price": "$0.00", "description": "Remote MCP server for AI agent integration (FREE)"},
        {"path": "/v1/indicators/{symbol}", "method": "GET", "price": "$0.02", "description": "Technical indicators: RSI, BB, ATR, S/R"},
        {"path": "/v1/yields", "method": "GET", "price": "$0.02", "description": "Top DeFi yield pools by TVL"},
        {"path": "/v1/metadata", "method": "GET", "price": "$0.01", "description": "URL metadata extraction and unfurling"},
        {"path": "/v1/search", "method": "GET", "price": "$0.01", "description": "AI-powered web search with structured results"},
        {"path": "/v1/disputes", "method": "POST", "price": "$0.05", "description": "Policy-driven dispute resolution (7 policy templates)"},
        {"path": "/v1/marketing/sentiment", "method": "POST", "price": "$0.03", "description": "AI brand sentiment analysis across platforms"},
        {"path": "/v1/marketing/trends", "method": "POST", "price": "$0.03", "description": "Industry trend detection with velocity scores"},
        {"path": "/v1/marketing/competitors", "method": "POST", "price": "$0.05", "description": "Competitive intelligence: keywords, channels, strategy"},
        {"path": "/v1/marketing/content-gaps", "method": "POST", "price": "$0.04", "description": "SEO content gap analysis"},
        {"path": "/v1/marketing/ad-copy", "method": "POST", "price": "$0.05", "description": "AI ad copy generator for paid channels"},
        {"path": "/v1/whales", "method": "GET", "price": "$0.02", "description": "Large whale transactions on BTC and ETH chains"},
        {"path": "/v1/exchange-flows", "method": "GET", "price": "$0.02", "description": "CEX reserve flows and 24h changes"},
        {"path": "/v1/correlation", "method": "GET", "price": "$0.03", "description": "30-day cross-asset correlation matrix"},
        {"path": "/v1/defi-tvl", "method": "GET", "price": "$0.02", "description": "DeFi protocol TVL rankings from DeFi Llama"},
        {"path": "/v1/stablecoin-flows", "method": "GET", "price": "$0.02", "description": "Stablecoin market caps and supply data"},
        {"path": "/v1/github-velocity", "method": "GET", "price": "$0.02", "description": "GitHub crypto repo velocity scores"},
        {"path": "/v1/macro", "method": "GET", "price": "$0.02", "description": "Macro economic and crypto indicators"},
        {"path": "/v1/research", "method": "GET", "price": "$0.05", "description": "Deep research — search + extract + synthesize in one call"},
        {"path": "/v1/portfolio", "method": "GET", "price": "$0.10", "description": "Portfolio intelligence — price + signal + risk + sentiment in one call"},
        {"path": "/v1/defi-strategy", "method": "GET", "price": "$0.25", "description": "DeFi strategy report — yields + TVL + comparison + risk analysis"},
        {"path": "/v1/market-pulse", "method": "GET", "price": "$0.05", "description": "Market pulse — sentiment + trending + news + whales + global snapshot"},
        {"path": "/v1/onchain-overview", "method": "GET", "price": "$0.15", "description": "On-chain overview — whales + exchange flows + stablecoin flows + correlation + DeFi TVL"},
    ]
    paid_endpoints = [endpoint for endpoint in endpoints if endpoint["price"] != "$0.00"]
    resources = [f"https://agentservices.to{e['path']}" for e in endpoints]
    return {
        "version": "1.0",
        "name": "AgentServices",
        "description": "Paid data APIs for AI agents — crypto, DeFi, on-chain analytics, search, marketing intelligence, and dispute resolution",
        "networks": X402_NETWORKS,
        "chain_id": X402_NETWORKS[0] if X402_NETWORKS else "eip155:8453",
        "currency": "USDC",
        "endpoints": endpoints,
        "resources": resources,
        "paid_endpoints": paid_endpoints,
        "paid_endpoint_count": len(paid_endpoints),
        "categories": ["Data", "Market Data", "On-chain Analytics", "Geolocation", "DEX", "Prediction Markets", "Search", "News", "Governance", "Dispute Resolution", "MCP", "Marketing Intelligence"],
        "payTo": X402_WALLET,
        "contact": "https://github.com/vbkotecha",
        "website": "https://agentservices.to",
        "repository": "https://github.com/vbkotecha/agentservices-api",
        "homepage": "https://agentservices.to",
        "license": "MIT",
        "spec": "x402-service-manifest/1",
    }


@app.get("/.well-known/x402-service.json")
async def x402_service_json():
    """x402 service manifest in true402/open marketplace format.
    Consumed by true402.dev, The Spawn, and other open x402 marketplaces."""
    return {
        "x402": "1.0",
        "name": "AgentServices",
        "description": "Paid APIs for AI agents — crypto data, stocks, SEC filings, commodities, FX, DeFi, on-chain analytics, search, marketing intelligence, and more. 53 services, 41 paid. All via x402 (USDC on Base).",
        "capabilities": ["data", "crypto", "defi", "onchain", "search", "marketing", "stocks", "commodities", "fx", "inference"],
        "pricing": {"currency": "USDC", "base": "0.01", "unit": "request"},
        "payment": {"address": X402_WALLET, "chain": "base", "facilitator": X402_FACILITATOR_URL},
        "endpoint": "https://agentservices.to",
        "website": "https://agentservices.to",
        "repository": "https://github.com/vbkotecha/agentservices-api",
        "contact": "https://github.com/vbkotecha",
        "license": "MIT",
    }


@app.get("/.well-known/agent.json")
async def agent_json():
    """Agent discovery manifest for AI agent platforms and crawlers."""
    return {
        "name": "AgentServices",
        "version": "5.3.0",
        "description": "Paid data APIs for AI agents — crypto, DeFi, DEX, prediction markets, news, search, geolocation, metadata, on-chain analytics, whale tracking, DeFi TVL, correlation matrix, stablecoin flows, GitHub velocity, macro indicators",
        "url": "https://agentservices.to",
        "capabilities": [
            "crypto-market-data",
            "technical-indicators",
            "defi-yields",
            "ip-geolocation",
            "url-metadata",
            "web-search",
            "dex-swap-quotes",
            "prediction-markets",
            "crypto-news",
            "social-trending",
            "global-market-stats",
            "marketing-sentiment",
            "marketing-trends",
            "marketing-competitors",
            "marketing-content-gaps",
            "marketing-ad-copy",
            "whale-tracking",
            "exchange-flows",
            "correlation-matrix",
            "defi-tvl",
            "stablecoin-flows",
            "github-velocity",
            "agent-context",
            "macro-indicators",
        ],
        "payment": {
            "protocol": "x402",
            "currency": "USDC",
            "network": "base-mainnet",
            "chain_id": 8453,
        },
        "endpoints": {
            "free": [
                "GET /v1/price/{symbol}",
                "GET /v1/prices?symbols=BTC,ETH",
                "GET /v1/fear-greed",
                "GET /v1/geo/{ip}",
                "GET /v1/global",
                "GET /v1/trending",
                "GET /v1/gas",
                "GET /v1/swap/quote",
                "GET /v1/predictions",
                "GET /v1/news",
                "GET /v1/social",
            ],
            "paid": [
                {"path": "GET /v1/indicators/{symbol}", "price": "$0.02"},
                {"path": "GET /v1/yields", "price": "$0.02"},
                {"path": "GET /v1/metadata", "price": "$0.01"},
                {"path": "GET /v1/search", "price": "$0.01"},
                {"path": "POST /v1/disputes", "price": "$0.05"},
                {"path": "POST /v1/marketing/sentiment", "price": "$0.03"},
                {"path": "POST /v1/marketing/trends", "price": "$0.03"},
                {"path": "POST /v1/marketing/competitors", "price": "$0.05"},
                {"path": "POST /v1/marketing/content-gaps", "price": "$0.04"},
                {"path": "POST /v1/marketing/ad-copy", "price": "$0.05"},
                {"path": "GET /v1/whales", "price": "$0.02"},
                {"path": "GET /v1/exchange-flows", "price": "$0.02"},
                {"path": "GET /v1/correlation", "price": "$0.03"},
                {"path": "GET /v1/defi-tvl", "price": "$0.02"},
                {"path": "GET /v1/stablecoin-flows", "price": "$0.02"},
                {"path": "GET /v1/github-velocity", "price": "$0.02"},
                {"path": "GET /v1/macro", "price": "$0.02"},
            ],
        },
        "docs": "https://agentservices.to/docs",
        "github": "https://github.com/vbkotecha/agentservices-api",
        "wallet": X402_WALLET,
    }


@app.get("/.well-known/mcp.json")
@app.get("/mcp.json", include_in_schema=False)
async def mcp_well_known():
    """MCP discovery file for mcpub and other MCP directory crawlers."""
    return {
        "name": "AgentServices",
        "version": "5.3.0",
        "description": "50+ x402-paid crypto/market data APIs for AI agents. 37 MCP tools across 54 services.",
        "mcp_endpoint": "https://agentservices.to/mcp",
        "website": "https://agentservices.to",
    }


@app.get("/server.json", include_in_schema=False)
async def server_json():
    """MCP Registry manifest for GEO/discovery crawlers."""
    path = Path(__file__).parent.parent / "server.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="not found")
    return json.loads(path.read_text())


@app.get("/.well-known/x402.json")
async def x402_json_manifest():
    """x402 v2 discovery manifest — what AgentGrade, Open 402 Directory, and x402.direct crawlers look for."""
    paid_services = [
        {"method": "GET", "path": "/v1/indicators/{symbol}", "price": "$0.02"},
        {"method": "GET", "path": "/v1/yields", "price": "$0.02"},
        {"method": "GET", "path": "/v1/metadata", "price": "$0.01"},
        {"method": "GET", "path": "/v1/search", "price": "$0.01"},
        {"method": "POST", "path": "/v1/disputes", "price": "$0.05"},
        {"method": "POST", "path": "/v1/marketing/sentiment", "price": "$0.03"},
        {"method": "POST", "path": "/v1/marketing/trends", "price": "$0.03"},
        {"method": "POST", "path": "/v1/marketing/competitors", "price": "$0.05"},
        {"method": "POST", "path": "/v1/marketing/content-gaps", "price": "$0.04"},
        {"method": "POST", "path": "/v1/marketing/ad-copy", "price": "$0.05"},
        {"method": "GET", "path": "/v1/whales", "price": "$0.02"},
        {"method": "GET", "path": "/v1/exchange-flows", "price": "$0.02"},
        {"method": "GET", "path": "/v1/correlation", "price": "$0.03"},
        {"method": "GET", "path": "/v1/defi-tvl", "price": "$0.02"},
        {"method": "GET", "path": "/v1/stablecoin-flows", "price": "$0.02"},
        {"method": "GET", "path": "/v1/github-velocity", "price": "$0.02"},
        {"method": "GET", "path": "/v1/macro", "price": "$0.02"},
        {"method": "POST", "path": "/v1/inference", "price": "$0.03"},
        {"method": "POST", "path": "/v1/complete", "price": "$0.03"},
        {"method": "GET", "path": "/v1/token-risk/{token}", "price": "$0.03"},
        {"method": "GET", "path": "/v1/signals/{symbol}", "price": "$0.04"},
        {"method": "GET", "path": "/v1/hn-sentiment", "price": "$0.02"},
        {"method": "GET", "path": "/v1/npm-stats/{package}", "price": "$0.02"},
        {"method": "GET", "path": "/v1/github-trending", "price": "$0.02"},
        {"method": "GET", "path": "/v1/yield-comparison", "price": "$0.03"},
        # Traditional Finance (v5.1.0)
        {"method": "GET", "path": "/v1/stocks/{ticker}", "price": "$0.02"},
        {"method": "GET", "path": "/v1/stocks/{ticker}/history", "price": "$0.03"},
        {"method": "GET", "path": "/v1/sec/{ticker}", "price": "$0.03"},
        {"method": "GET", "path": "/v1/commodities", "price": "$0.03"},
        {"method": "GET", "path": "/v1/economic", "price": "$0.03"},
        {"method": "GET", "path": "/v1/fx", "price": "$0.003"},
        # Utility (v5.1.0)
        {"method": "GET", "path": "/v1/extract", "price": "$0.002"},
        {"method": "GET", "path": "/v1/security/{package}", "price": "$0.02"},
        {"method": "GET", "path": "/v1/seo/keywords", "price": "$0.01"},
        # Intelligence (bundled high-value)
        {"method": "GET", "path": "/v1/research", "price": "$0.05"},
        {"method": "GET", "path": "/v1/portfolio/{symbol}", "price": "$0.10"},
        {"method": "GET", "path": "/v1/defi-strategy", "price": "$0.25"},
        {"method": "GET", "path": "/v1/market-pulse", "price": "$0.05"},
        {"method": "GET", "path": "/v1/onchain-overview", "price": "$0.15"},
        {"method": "GET", "path": "/v1/arbitrage", "price": "$0.08"},
        {"method": "GET", "path": "/v1/liquidation-map", "price": "$0.12"},
    ]
    free_services = [
        {"method": "GET", "path": "/v1/price/{symbol}", "price": "$0.00"},
        {"method": "GET", "path": "/v1/prices", "price": "$0.00"},
        {"method": "GET", "path": "/v1/fear-greed", "price": "$0.00"},
        {"method": "GET", "path": "/v1/global", "price": "$0.00"},
        {"method": "GET", "path": "/v1/trending", "price": "$0.00"},
        {"method": "GET", "path": "/v1/gas", "price": "$0.00"},
        {"method": "GET", "path": "/v1/geo/{ip}", "price": "$0.00"},
        {"method": "GET", "path": "/v1/swap/quote", "price": "$0.00"},
        {"method": "GET", "path": "/v1/predictions", "price": "$0.00"},
        {"method": "GET", "path": "/v1/news", "price": "$0.00"},
        {"method": "GET", "path": "/v1/social", "price": "$0.00"},
        {"method": "GET", "path": "/v1/policies", "price": "$0.00"},
        {"method": "POST", "path": "/mcp", "price": "$0.00"},
    ]
    from datetime import datetime, timezone
    return {
        "x402Version": 2,
        "name": "AgentServices",
        "description": "Paid APIs for AI agents — crypto data, stocks, SEC filings, commodities, FX, inference gateway, market signals, web extraction, security scanning, MCP integration, cross-DEX arbitrage scanning. 53 services, 41 paid.",
        "network": "eip155:8453",
        "facilitator": {
            "type": "coinbase",
            "url": "https://agentservices.to",
            "description": "Coinbase Developer Platform (CDP) x402 facilitator on Base mainnet"
        },
        "payTo": X402_WALLET,
        "currency": "USDC",
        "website": "https://agentservices.to",
        "apiBaseUrl": "https://agentservices.to",
        "repository": "https://github.com/vbkotecha/agentservices-api",
        "documentation": "https://agentservices.to/docs",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "services": paid_services + free_services,
        "resources": [f"https://agentservices.to{s['path']}" for s in paid_services + free_services],
        "extensions": {
            "bazaar": {
                "discoverable": True,
                "name": "AgentServices",
                "description": "Paid APIs for AI agents — crypto data, market intelligence, on-chain analytics, DeFi strategy, cross-DEX arbitrage, AI inference. 53 services, 41 paid.",
                "category": "data",
                "tags": ["data", "crypto", "defi", "search", "inference", "market-intelligence", "onchain", "analytics"],
            },
            "listing": {
                "name": "AgentServices",
                "description": "53 paid APIs for AI agents. Data, search, market intelligence, and services agents pay for via x402.",
                "category": "Data & APIs",
                "pricing_model": "per-request",
                "price_range": "$0.002 - $0.25",
                "tags": ["crypto", "defi", "market-data", "analytics", "inference", "search", "onchain", "x402"],
            }
        },
    }


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml():
    """XML sitemap for search engines and AI crawlers."""
    from starlette.responses import Response
    urls = [
        "https://agentservices.to",
        "https://agentservices.to/docs",
        "https://agentservices.to/examples",
        "https://agentservices.to/llms.txt",
        "https://agentservices.to/.well-known/llms.txt",
        "https://agentservices.to/llms-full.txt",
        "https://agentservices.to/openapi.json",
        "https://agentservices.to/.well-known/openapi.json",
        "https://agentservices.to/feed.json",
        "https://agentservices.to/server.json",
        "https://agentservices.to/mcp.json",
        "https://agentservices.to/agents.txt",
        "https://agentservices.to/.well-known/x402.json",
        "https://agentservices.to/.well-known/mcp/server-card.json",
        "https://agentservices.to/.well-known/ai-catalog.json",
        "https://agentservices.to/.well-known/agent-card.json",
        "https://agentservices.to/.well-known/agentskills/agentservices/SKILL.md",
    ]
    xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_parts.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for url in urls:
        xml_parts.append(f"  <url><loc>{url}</loc><changefreq>daily</changefreq><priority>0.8</priority></url>")
    xml_parts.append('</urlset>')
    return Response(content="\n".join(xml_parts), media_type="application/xml")


@app.get("/llms-full.txt", include_in_schema=False)
async def llms_full_txt():
    """Full site content in clean markdown for LLM context windows."""
    from starlette.responses import PlainTextResponse
    lines = [
        "# AgentServices — Complete API Reference",
        "",
        "> Paid APIs for AI agents. 53 services, 41 paid. Data, search, market intelligence, inference, and services agents pay for via x402 (USDC on Base).",
        "",
        "## What is AgentServices?",
        "",
        "AgentServices is a paid API platform for AI agents. Agents discover and pay for data, search, market intelligence, and other services via x402 (USDC on Base). 53 endpoints, 41 paid, MCP integration, and cross-DEX arbitrage scanning.",
        "",
        "## Base URL",
        "https://agentservices.to",
        "",
        "## Authentication",
        "Paid endpoints use the x402 protocol (USDC on Base Mainnet, chain ID 8453). Free endpoints require no authentication.",
        f"Payment wallet: {X402_WALLET}",
        "",
        "## Free Endpoints (No Payment Required)",
        "",
        "### Cryptocurrency",
        "- GET /v1/price/{symbol} — Current crypto price (BTC, ETH, SOL, etc.)",
        "- GET /v1/prices?symbols=BTC,ETH,SOL — Batch crypto prices",
        "- GET /v1/fear-greed — Crypto Fear & Greed Index (0-100 scale)",
        "- GET /v1/global — Global market cap, 24h volume, BTC dominance",
        "- GET /v1/trending — Trending tokens being searched right now",
        "- GET /v1/gas — Current Ethereum gas prices (slow/standard/fast in Gwei)",
        "- GET /v1/swap/quote?chain=ethereum&tokenIn=...&tokenOut=... — DEX swap quote (0x API, 6 chains)",
        "",
        "### Prediction Markets",
        "- GET /v1/predictions — Active Polymarket prediction markets",
        "- GET /v1/predictions/{slug} — Specific prediction market details",
        "",
        "### News & Social",
        "- GET /v1/news — Latest crypto and blockchain news headlines",
        "- GET /v1/social — Trending coins, categories, NFTs from social signals",
        "",
        "### Utility",
        "- GET /v1/geo/{ip} — IP geolocation lookup (city, country, ISP, coordinates)",
        "- GET /v1/policies — List dispute policy templates",
        "- GET /v1/agent-context — Paste-ready market context for LLM prompts",
        "- POST /mcp — MCP server (JSON-RPC over Streamable HTTP (MCP v2 stateless), 37 tools)",
        "",
        "## Paid Endpoints (x402 / USDC on Base)",
        "",
        "### Crypto Data & Analytics ($0.01-$0.04)",
        "- GET /v1/indicators/{symbol} — Technical indicators: RSI, Bollinger Bands, ATR, Support/Resistance ($0.02)",
        "- GET /v1/yields — Top DeFi yield pools by TVL across chains ($0.02)",
        "- GET /v1/metadata?url=... — URL metadata extraction and unfurling ($0.01)",
        "- GET /v1/search?q=... — AI-powered web search ($0.01)",
        "- GET /v1/whales — Large whale transactions for BTC/ETH ($0.02)",
        "- GET /v1/exchange-flows — CEX reserve flows and netflow ($0.02)",
        "- GET /v1/correlation — 30-day cross-asset correlation matrix ($0.03)",
        "- GET /v1/defi-tvl — DeFi protocol TVL rankings ($0.02)",
        "- GET /v1/stablecoin-flows — Stablecoin market caps and supply changes ($0.02)",
        "- GET /v1/github-velocity — GitHub crypto repo velocity scores ($0.02)",
        "- GET /v1/macro — Macro economic indicators: CPI, GDP, Fed rate ($0.02)",
        "- GET /v1/token-risk/{token} — Token risk scoring (0-100) ($0.03)",
        "- GET /v1/signals/{symbol} — Crypto buy/sell signals with confidence ($0.04)",
        "- GET /v1/hn-sentiment — Hacker News tech sentiment analysis ($0.02)",
        "- GET /v1/npm-stats/{package} — NPM download trends ($0.02)",
        "- GET /v1/github-trending — GitHub trending repos (daily/weekly) ($0.02)",
        "- GET /v1/yield-comparison — DeFi yield comparison with risk assessment ($0.03)",
        "",
        "### Traditional Finance ($0.003-$0.03)",
        "- GET /v1/stocks/{ticker} — Real-time stock quote ($0.02)",
        "- GET /v1/stocks/{ticker}/history — Historical OHLCV data ($0.03)",
        "- GET /v1/sec/{ticker} — SEC filings parser: 10-K, 10-Q, Form 4 ($0.03)",
        "- GET /v1/commodities — Oil, gold, silver, wheat prices ($0.03)",
        "- GET /v1/economic — CPI, GDP, unemployment, Fed rate (FRED) ($0.03)",
        "- GET /v1/fx?base=USD — 30+ currency exchange rates ($0.003)",
        "",
        "### Utility ($0.002-$0.02)",
        "- GET /v1/extract?url=... — Web content extraction, clean text from any URL ($0.002)",
        "- GET /v1/security/{package} — Package vulnerability scan (PyPI/npm) ($0.02)",
        "- GET /v1/seo/keywords?keyword=... — SEO keyword research with volume ($0.01)",
        "",
        "### AI Inference ($0.03)",
        "- POST /v1/inference — LLM inference gateway (gpt-5.4, gpt-5.4-mini, gpt-5.5, gemini) ($0.03)",
        "- POST /v1/complete?prompt=... — Quick text completion ($0.03)",
        "",
        "### Bundled Intelligence ($0.05-$0.25)",
        "- GET /v1/research?q=... — Deep research: search + extract + synthesize ($0.05)",
        "- GET /v1/portfolio?symbol=... — Portfolio intelligence: price + signal + risk + sentiment ($0.10)",
        "- GET /v1/defi-strategy?chain=... — DeFi strategy: yields + TVL + comparison + risk ($0.25)",
        "- GET /v1/market-pulse — Market pulse: sentiment + trending + news + whales + global ($0.05)",
        "- GET /v1/onchain-overview — On-chain: whales + flows + correlation + DeFi TVL ($0.15)",
        "- GET /v1/arbitrage?symbols=... — Cross-DEX arbitrage scanner with gas-adjusted profitability ($0.08)",
        "",
        "### Marketing Intelligence ($0.03-$0.05)",
        "- POST /v1/marketing/sentiment — AI brand sentiment analysis ($0.03)",
        "- POST /v1/marketing/trends — Industry trend detection with velocity ($0.03)",
        "- POST /v1/marketing/competitors — Competitive intelligence ($0.05)",
        "- POST /v1/marketing/content-gaps — SEO content gap analysis ($0.04)",
        "- POST /v1/marketing/ad-copy — AI ad copy generator ($0.05)",
        "",
        "### Dispute Resolution",
        "- POST /v1/disputes — Submit dispute for policy-driven ruling ($0.05)",
        "",
        "### Voice",
        "- GET /v1/phone — AgentServices phone number info (FREE)",
        "- POST /v1/calls — Make outbound AI voice call ($0.54)",
        "- GET /v1/lookup/{phone} — Phone number carrier lookup ($0.05)",
        "",
        "## Example Usage",
        "",
        "```bash",
        "# Free: Get BTC price",
        "curl https://agentservices.to/v1/price/BTC",
        "",
        "# Paid: Get BTC technical indicators (returns 402 without payment)",
        "curl https://agentservices.to/v1/indicators/BTC",
        "",
        "# Free: Batch prices",
        "curl 'https://agentservices.to/v1/prices?symbols=BTC,ETH,SOL'",
        "",
        "# Free: Trending tokens",
        "curl https://agentservices.to/v1/trending",
        "```",
        "",
        "## MCP Integration",
        "",
        "AgentServices provides a remote MCP server at https://agentservices.to/mcp with 37 tools.",
"""
MCP config for Claude Desktop:
{\"mcpServers\":{\"agentservices\":{\"url\":\"https://agentservices.to/mcp\"}}}
""",
        "",
        "## Payment Protocol",
        "",
        "AgentServices uses x402 version 2. Agents pay per call with USDC on Base (chain ID 8453).",
        "- Discovery: /.well-known/x402.json",
        "- 402 response includes: payment amount, payTo address, network, asset contract, Bazaar extension",
        f"- Revenue wallet: {X402_WALLET}",
        "",
        "## Discovery Files",
        "- /.well-known/x402.json — x402 v2 payment manifest",
        "- /.well-known/x402-service.json — x402 service listing format",
        "- /.well-known/mcp/server-card.json — MCP server card",
        "- /.well-known/ai-catalog.json — ARD (Agentic Resource Discovery) catalog",
        "- /.well-known/ai-plugin.json — OpenAI plugin manifest",
        "- /.well-known/agent-card.json — Agent identity card",
        "- /.well-known/agentskills/agentservices/SKILL.md — AgentSkills.io skill",
        "- /.well-known/agent-skills/index.json — Agent skills index",
        "- /openapi.json — OpenAPI 3.1 specification with x-payment-info",
        "- /robots.txt — AI crawler rules with Content-Signal directives",
        "- /sitemap.xml — XML sitemap",
        "- /feed.json — JSON Feed",
        "- /llms.txt — Concise LLM-readable description",
        "- /examples — Agent integration guide with curl examples",
        "",
        "## Links",
        "- API Docs (Swagger): https://agentservices.to/docs",
        "- Integration Examples: https://agentservices.to/examples",
        "- GitHub: https://github.com/vbkotecha/agentservices-api",
        "- x402 Manifest: https://agentservices.to/.well-known/x402.json",
        "",
        "## SDK",
        "- Python: pip install agentservices (LangChain + CrewAI tools included)",
        "- MCP: npx agentservices-mcp (pure JavaScript, zero dependencies)",
        "- ElizaOS: @agentservices/plugin-elizaos (12 actions + market context provider)",
        "- AgentKit: @agentservices/agentkit-provider (18 actions for Coinbase AgentKit)",
    ]
    return PlainTextResponse(content="\n".join(lines), media_type="text/plain")


@app.get("/feed.json", include_in_schema=False)
async def json_feed():
    """JSON Feed (https://jsonfeed.org/) for content syndication."""
    return {
        "version": "https://jsonfeed.org/version/1.1",
        "title": "AgentServices",
        "description": "Paid APIs for AI agents — data, search, market intelligence, and services agents pay for via x402.",
        "home_page_url": "https://agentservices.to",
        "feed_url": "https://agentservices.to/feed.json",
        "authors": [{"name": "AgentServices", "url": "https://agentservices.to"}],
        "items": [
            {
                "id": "https://agentservices.to",
                "url": "https://agentservices.to",
                "title": "AgentServices — 52 Paid APIs for AI Agents",
                "content_text": "Paid APIs for AI agents. 53 services, 41 paid. Crypto data, stocks, SEC filings, commodities, FX, inference gateway, market signals, web extraction, security scanning, MCP integration, cross-DEX arbitrage. All via x402 (USDC on Base).",
                "date_published": "2026-07-08T00:00:00Z",
                "tags": ["x402", "api", "ai-agents", "crypto", "defi", "mcp"],
            },
            {
                "id": "https://agentservices.to/examples",
                "url": "https://agentservices.to/examples",
                "title": "Agent Integration Examples",
                "content_text": "Step-by-step guide for agents to discover, pay for, and use AgentServices endpoints. Includes MCP config, curl examples, and use cases.",
                "date_published": "2026-07-08T00:00:00Z",
            },
            {
                "id": "https://agentservices.to/.well-known/x402.json",
                "url": "https://agentservices.to/.well-known/x402.json",
                "title": "x402 Payment Discovery Manifest",
                "content_text": "x402 v2 manifest listing all 53 services with pricing, payment address, and Bazaar metadata.",
                "date_published": "2026-07-08T00:00:00Z",
            },
        ],
    }


@app.get("/.well-known/agent-card.json", include_in_schema=False)
async def agent_card():
    """Agent Card — agent identity for inter-agent communication and discovery."""
    return {
        "@context": "https://www.w3.org/ns/did/v1",
        "id": "did:web:agentservices.to",
        "name": "AgentServices",
        "description": "Paid APIs for AI agents. 53 services, 41 paid. Data, search, market intelligence, inference, and services agents pay for via x402.",
        "type": "Service",
        "protocolVersion": "1.0",
        "version": "5.3.0",
        "url": "https://agentservices.to",
        "logo": "https://agentservices.to/favicon.ico",
        "skills": [
            {
                "id": "agent-initiated-checkout",
                "name": "Agent-Initiated Checkout (AP2)",
                "description": "Paid APIs for AI agents over x402: market data, research, inference, portfolio intelligence, and payment-aware tooling.",
                "tags": ["x402", "payments", "market-intelligence", "research", "inference", "mcp"],
            }
        ],
        "endpoints": {
            "api": "https://agentservices.to",
            "mcp": "https://agentservices.to/mcp",
            "openapi": "https://agentservices.to/openapi.json",
            "docs": "https://agentservices.to/docs",
            "examples": "https://agentservices.to/examples",
            "health": "https://agentservices.to/health",
        },
        "capabilities": {
            "services": [
                "crypto_prices", "technical_indicators", "defi_yields", "fear_greed",
                "market_intelligence", "portfolio_analysis", "defi_strategy",
                "cross_dex_arbitrage", "onchain_analytics", "ai_inference",
                "web_search", "web_extraction", "token_risk_scoring",
                "crypto_signals", "whale_tracking", "exchange_flows",
                "stock_quotes", "sec_filings", "commodities", "fx_rates",
                "marketing_intelligence", "dispute_resolution",
            ],
            "payment": {
                "protocol": "x402",
                "version": 2,
                "network": "eip155:8453",
                "asset": "USDC",
                "payTo": X402_WALLET,
            },
            "integration": {
                "mcp": True,
                "rest": True,
                "python_sdk": "pip install agentservices",
                "mcp_server": "npx agentservices-mcp",
            },
        },
        "serviceCount": 53,
        "paidServiceCount": 41,
    }


@app.get("/.well-known/agent-skills/index.json", include_in_schema=False)
async def agent_skills_index():
    """Agent Skills index — lists all available agent skills per agentskills.io spec."""
    return {
        "schemaVersion": "1.0",
        "name": "AgentServices",
        "description": "Paid APIs for AI agents.",
        "url": "https://agentservices.to",
        "skills": [
            {
                "name": "agentservices",
                "description": "53 paid APIs for AI agents — crypto data, market intelligence, on-chain analytics, DeFi strategy, cross-DEX arbitrage, AI inference, web extraction, and more.",
                "manifest": "https://agentservices.to/.well-known/agentskills/agentservices/SKILL.md",
                "version": "5.3.0",
                "license": "MIT",
                "payment": {
                    "protocol": "x402",
                    "network": "eip155:8453",
                    "asset": "USDC",
                },
            },
        ],
    }


@app.get("/.well-known/ai-catalog.json")
async def ai_catalog():
    """Agentic Resource Discovery (ARD) catalog — Google Cloud Agent Registry + federated discovery.
    Spec: github.com/ards-project/ard-spec — makes AgentServices discoverable by Gemini Enterprise agents."""
    return {
        "specVersion": "1.0",
        "host": {
            "displayName": "AgentServices",
            "identifier": "urn:ai:::agentservices.to",
            "documentationUrl": "https://agentservices.to",
        },
        "entries": [
            {
                "identifier": "urn:ai:::agentservices.to/mcp",
                "displayName": "AgentServices MCP Server",
                "type": "application/mcp-server-card+json",
                "url": "https://agentservices.to/mcp",
                "description": "53 paid APIs for AI agents — crypto data, market intelligence, on-chain analytics, cross-DEX arbitrage, AI inference, DeFi strategy, portfolio intelligence. 38 MCP tools. x402 payments (USDC on Base).",
                "tags": ["crypto", "defi", "market-data", "x402", "payments", "analytics", "inference", "mcp", "agents", "blockchain"],
                "capabilities": [
                    "crypto_prices", "technical_indicators", "defi_yields", "fear_greed",
                    "market_intelligence", "portfolio_analysis", "defi_strategy",
                    "cross_dex_arbitrage", "onchain_analytics", "ai_inference",
                    "web_search", "web_extraction", "token_risk_scoring",
                    "crypto_signals", "whale_tracking", "exchange_flows",
                ],
                "representativeQueries": [
                    "get Bitcoin price and technical indicators",
                    "find the best DeFi yield opportunities",
                    "analyze my crypto portfolio risk",
                    "scan for cross-DEX arbitrage opportunities",
                    "run AI inference with GPT or Gemini models",
                ],
                "version": "5.3.0",
                "updatedAt": "2026-07-08T07:00:00Z",
                "metadata": {
                    "pricing": "freemium ($0.01-$0.25 per call, USDC on Base)",
                    "paymentProtocol": "x402",
                    "chain": "base",
                    "endpointCount": "52",
                    "freeEndpoints": "12",
                    "paidEndpoints": "40",
                    "openapiSpec": "https://agentservices.to/openapi.json",
                    "skillCard": "https://agentservices.to/.well-known/agentskills/agentservices/SKILL.md",
                    "x402Manifest": "https://agentservices.to/.well-known/x402.json",
                },
            },
            {
                "identifier": "urn:ai:::agentservices.to/api",
                "displayName": "AgentServices REST API",
                "type": "application/vnd.oai.openapi+json",
                "url": "https://agentservices.to/openapi.json",
                "description": "REST API with 53 endpoints for crypto data, stocks, SEC filings, commodities, FX rates, web search, extraction, SEO analysis, package security, GitHub trending, HN sentiment, npm stats, and more.",
                "tags": ["api", "rest", "crypto", "finance", "data", "analytics"],
                "capabilities": ["rest_api", "data_endpoints", "synthesis", "market_data"],
                "representativeQueries": [
                    "get crypto prices and market data",
                    "analyze stock fundamentals and SEC filings",
                    "extract content from web pages",
                    "check npm package security",
                ],
                "version": "5.3.0",
                "updatedAt": "2026-07-08T07:00:00Z",
            },
        ],
    }


@app.get("/robots.txt")
async def robots_txt():
    """Robots.txt with explicit AI crawler rules for agent discovery."""
    from starlette.responses import PlainTextResponse
    lines = [
        "# AgentServices — robots.txt",
        "# AI agents and crawlers are explicitly allowed",
        "",
        "User-agent: GPTBot",
        "Allow: /",
        "",
        "User-agent: ClaudeBot",
        "Allow: /",
        "",
        "User-agent: ChatGPT-User",
        "Allow: /",
        "",
        "User-agent: anthropic-ai",
        "Allow: /",
        "",
        "User-agent: Google-Extended",
        "Allow: /",
        "",
        "User-agent: PerplexityBot",
        "Allow: /",
        "",
        "User-agent: Amazonbot",
        "Allow: /",
        "",
        "User-agent: *",
        "Allow: /",
        "",
        "# Key endpoints for AI agents",
        "# /llms.txt — Machine-readable service description",
        "# /llms-full.txt — Full site content in markdown",
        "# /openapi.json — OpenAPI 3.1 specification",
        "# /mcp — MCP server (Streamable HTTP)",
        "# /sitemap.xml — Sitemap",
        "# /feed.json — JSON Feed",
        "# /.well-known/x402 — x402 payment discovery",
        "# /.well-known/x402.json — x402 v2 manifest",
        "# /.well-known/mcp/server-card.json — MCP server card",
        "# /.well-known/ai-catalog.json — ARD catalog",
        "# /.well-known/agent-card.json — Agent card",
        "# /.well-known/agent-skills/index.json — Agent skills index",
        "",
        "# AI Content Signals",
        "Content-Signal: llms-txt on",
        "Content-Signal: llms-full-txt on",
        "Content-Signal: openapi on",
        "Content-Signal: mcp on",
        "Content-Signal: x402 on",
        "",
        "# Sitemap",
        "Sitemap: https://agentservices.to/sitemap.xml",
    ]
    return PlainTextResponse(content="\n".join(lines), media_type="text/plain")


@app.get(f"/{INDEXNOW_KEY}.txt", include_in_schema=False)
async def indexnow_key():
    """IndexNow key verification file for search engine URL submission."""
    return PlainTextResponse(content=INDEXNOW_KEY, media_type="text/plain")


@app.get("/schema.json")
@app.get("/.well-known/openapi.json", include_in_schema=False)
async def openapi_schema():
    """OpenAPI schema aliases for crawlers: /schema.json and /.well-known/openapi.json (same body as /openapi.json)."""
    return app.openapi()


@app.get("/.well-known/agentskills/agentservices/SKILL.md")
async def agentskills_manifest():
    """AgentSkills.io SKILL.md — discoverable skill for agent platforms (AIsa, etc)."""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        content='''---
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

# AgentServices -- Paid Data APIs for AI Agents

## Overview

AgentServices provides 50 API endpoints for AI agents, covering crypto data,
on-chain analytics, market intelligence, web research, and AI inference.
Paid endpoints use x402 micropayments ($0.01-$0.25 per call in USDC on Base).
12 endpoints are completely free -- no payment, no signup, no API key.

## Quick Start

### Free Endpoints (no payment, no key)

    curl https://agentservices.to/v1/prices
    curl https://agentservices.to/v1/price/BTC
    curl https://agentservices.to/v1/fear-greed
    curl https://agentservices.to/v1/trending
    curl https://agentservices.to/v1/news
    curl https://agentservices.to/v1/global

### Paid Endpoints (x402 micropayment)

When you call a paid endpoint, the server returns HTTP 402 with payment
instructions in the response body. Pay with USDC on Base, then retry
with the payment proof.

## Payment Setup

### Option 1: Coinbase Agentic Wallet (recommended)

Install the agentic wallet CLI and fund with USDC on Base:

    npx awal@latest wallet generate
    npx awal@latest wallet fund --amount 5    # $5 USDC

Then pay for any endpoint:

    npx awal@latest x402 pay 'https://agentservices.to/v1/indicators/BTC'

### Option 2: Any x402-compatible wallet

Use @x402/fetch or any x402 client library. The server's 402 response
includes a complete payment descriptor (amount, payTo address, network,
and facilitator URL).

CDP Paymaster makes payments gasless -- no ETH needed, only USDC.

## MCP Integration

Connect AgentServices to any MCP-compatible client (Claude Desktop,
Cursor, Cline, Windsurf, VS Code):

### Claude Desktop

Add to claude_desktop_config.json:

    {
      "mcpServers": {
        "agentservices": {
          "url": "https://agentservices.to/mcp"
        }
      }
    }

### Cursor / Cline / Generic MCP Client

    Server URL: https://agentservices.to/mcp
    Transport: Streamable HTTP

37 tools available covering all endpoints.

## Endpoint Reference

### Free Endpoints (no payment)

| Endpoint | Description |
|---|---|
| GET /v1/prices | All crypto prices |
| GET /v1/price/{symbol} | Single crypto price |
| GET /v1/fear-greed | Fear & Greed Index |
| GET /v1/trending | Trending tokens |
| GET /v1/news | Latest crypto news |
| GET /v1/global | Global market stats |
| GET /v1/social-trending | Social media trends |
| GET /v1/gas | Gas prices |
| GET /v1/predictions | Price predictions |
| GET /v1/swap-quote | DEX swap quotes |
| GET /v1/geo | IP geolocation |
| GET /v1/policies | Dispute templates |

### Paid Endpoints (x402)

| Endpoint | Price | Description |
|---|---|---|
| GET /v1/indicators/{symbol} | $0.02 | Technical indicators (RSI, MACD, etc.) |
| GET /v1/yields | $0.02 | DeFi yield rates across protocols |
| GET /v1/whales | $0.02 | Whale transaction tracking |
| GET /v1/exchange-flows | $0.02 | Exchange inflow/outflow data |
| GET /v1/correlation | $0.03 | Token correlation matrix |
| GET /v1/stablecoin-flows | $0.02 | Stablecoin flow analysis |
| GET /v1/defi-tvl | $0.02 | DeFi TVL by protocol |
| GET /v1/search | $0.01 | Web search |
| GET /v1/metadata | $0.01 | URL metadata extraction |
| GET /v1/sentiment | $0.03 | Market sentiment analysis |
| GET /v1/trends | $0.03 | Market trend analysis |
| GET /v1/competitors | $0.05 | Competitor analysis |
| GET /v1/token-risk/{symbol} | $0.03 | Token risk assessment |
| GET /v1/crypto-signals/{symbol} | $0.04 | Crypto trading signals |
| GET /v1/portfolio?symbol=BTC | $0.10 | Portfolio intelligence report |
| GET /v1/defi-strategy | $0.25 | DeFi investment strategy report |
| GET /v1/market-pulse | $0.05 | Market overview (6 modules) |
| GET /v1/onchain-overview | $0.15 | On-chain analytics (5 modules) |
| GET /v1/research | $0.05 | Deep research (search+extract+synthesize) |
| POST /v1/inference | $0.03 | AI inference (GPT models) |
| POST /v1/complete | $0.03 | AI text completion |

Full list at https://agentservices.to/docs

## Use Cases

- **Portfolio Monitor**: /v1/portfolio + /v1/indicators + /v1/token-risk
- **DeFi Yield Optimizer**: /v1/defi-strategy + /v1/yields + /v1/defi-tvl
- **Market Intelligence Agent**: /v1/market-pulse + /v1/sentiment + /v1/trends
- **Trading Bot**: /v1/crypto-signals + /v1/whales + /v1/exchange-flows
- **Research Agent**: /v1/research + /v1/search + /v1/metadata

## Discovery

- x402 Manifest: https://agentservices.to/.well-known/x402.json
- OpenAPI Spec: https://agentservices.to/openapi.json
- Agent Skill Card: https://agentservices.to/.well-known/mcp/server-card.json
- ARD Catalog: https://agentservices.to/.well-known/ai-catalog.json
- MCP Registry: to.agentservices/agentservices
- Network: Base (eip155:8453)
- Facilitator: Coinbase CDP (https://api.cdp.coinbase.com/platform/v2/x402)
''',
        media_type="text/markdown",
        headers={"Cache-Control": "public, max-age=3600"}
    )


@app.get("/manifest.json")
async def web_manifest():
    """Web app manifest for browser/agent discovery."""
    return {
        "name": "AgentServices",
        "short_name": "AgentServices",
        "description": "Paid data APIs for AI agents — crypto, DeFi, geo, web metadata, marketing intelligence, dispute resolution",
        "start_url": "https://agentservices.to",
        "scope": "/",
        "display": "standalone",
        "categories": ["developer", "finance", "data"],
        "icons": [],
    }


@app.get("/.well-known/ai-plugin.json")
async def ai_plugin_manifest():
    """OpenAI plugin manifest for ChatGPT plugin discovery."""
    return {
        "schema_version": "v1",
        "name_for_human": "AgentServices",
        "name_for_model": "agentservices",
        "description_for_human": "Paid APIs for AI agents — crypto data, market intelligence, DeFi analytics, on-chain analytics, search, and AI inference. Pay per request with USDC on Base.",
        "description_for_model": "Access 50+ API endpoints for crypto prices, technical indicators, DeFi yields, on-chain analytics, whale tracking, market sentiment, web search, LLM inference, portfolio intelligence, and dispute resolution. Free endpoints need no payment. Paid endpoints use x402 protocol (USDC on Base).",
        "auth": {"type": "none"},
        "api": {"type": "openapi", "url": "https://agentservices.to/openapi.json"},
        "logo_url": "https://agentservices.to/logo.png",
        "contact_email": "vbkotecha@gmail.com",
        "legal_info_url": "https://agentservices.to",
        "url": "https://agentservices.to",
    }


def _self_hosted_docs_html(title: str = "AgentServices API Documentation") -> str:
    """Render a dependency-free endpoint index that works without CDN JavaScript."""
    spec = app.openapi()
    endpoint_rows = []
    for path, path_item in sorted(spec.get("paths", {}).items()):
        for method in ("get", "post", "put", "patch", "delete", "options", "head", "trace"):
            operation = path_item.get(method)
            if not operation:
                continue
            summary = operation.get("summary") or operation.get("description") or ""
            summary = str(summary).splitlines()[0][:220]
            tags = ", ".join(operation.get("tags", []))
            endpoint_rows.append(
                "<tr>"
                f'<td><span class="method {method.upper()}">{method.upper()}</span></td>'
                f"<td><code>{html.escape(path)}</code></td>"
                f"<td>{html.escape(summary)}</td>"
                f"<td>{html.escape(tags)}</td>"
                "</tr>"
            )
    rows = "".join(endpoint_rows)
    return f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>{html.escape(title)}</title>
<style>
:root{{color-scheme:dark}}body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#0b1020;color:#e8eefc;margin:0}}
main{{max-width:1200px;margin:auto;padding:36px 20px}}h1{{margin:0 0 8px;font-size:32px}}p{{color:#aab7d4}}a{{color:#83b4ff}}.links{{margin:22px 0}}
.table-wrap{{overflow:auto;border:1px solid #273452;border-radius:10px;background:#111a2d}}table{{width:100%;border-collapse:collapse;min-width:760px}}
th,td{{text-align:left;padding:12px 14px;border-bottom:1px solid #273452;vertical-align:top}}th{{background:#18233c;color:#bcd0f5;position:sticky;top:0}}tr:last-child td{{border-bottom:0}}code{{font-family:ui-monospace,SFMono-Regular,monospace;color:#d7a8ff}}
.method{{font-weight:700;font-size:12px;padding:4px 7px;border-radius:5px;background:#263652}}.GET{{color:#62e6a5}}.POST{{color:#ffd166}}.PUT,.PATCH{{color:#83b4ff}}.DELETE{{color:#ff8585}}
.badge{{display:inline-block;margin:4px 6px 4px 0;padding:5px 9px;border-radius:999px;background:#1a2947;color:#c5d7ff;font-size:13px}}
</style></head><body><main><h1>AgentServices</h1><p>{html.escape(spec.get("info", {}).get("description", "Paid APIs for AI agents."))}</p>
<div class=\"links\"><span class=\"badge\">OpenAPI {html.escape(str(spec.get("openapi", "3.1.0")))}</span><span class=\"badge\">{len(endpoint_rows)} operations</span><span class=\"badge\">{len(spec.get("paths", {}))} paths</span></div>
<p class=\"links\"><a href=\"/openapi.json\">Download OpenAPI JSON</a> · <a href=\"/docs-page\">Static docs</a></p>
<div class=\"table-wrap\"><table><thead><tr><th>Method</th><th>Path</th><th>Description</th><th>Tag</th></tr></thead><tbody>{rows}</tbody></table></div>
</main></body></html>"""


@app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
async def swagger_docs():
    return HTMLResponse(_self_hosted_docs_html("AgentServices — OpenAPI Documentation"))


@app.get("/redoc", response_class=HTMLResponse, include_in_schema=False)
async def redoc_docs():
    return HTMLResponse(_self_hosted_docs_html("AgentServices — ReDoc Documentation"))


@app.get("/docs-page", response_class=HTMLResponse)
async def api_docs_page():
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AgentServices — Premium APIs for AI Agents</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a0a;color:#e0e0e0;line-height:1.6}
.container{max-width:900px;margin:0 auto;padding:40px 20px}
header{text-align:center;margin-bottom:50px}
h1{font-size:2.5em;background:linear-gradient(135deg,#60a5fa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:10px}
.tagline{font-size:1.1em;color:#888}
.badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:0.85em;font-weight:600;margin:5px}
.badge-free{background:#1a3a1a;color:#4ade80;border:1px solid #4ade80}
.badge-paid{background:#3a2a1a;color:#fbbf24;border:1px solid #fbbf24}
.badge-x402{background:#2a1a3a;color:#a78bfa;border:1px solid #a78bfa}
section{background:#111;border-radius:12px;padding:25px;margin-bottom:20px;border:1px solid #222}
h2{font-size:1.4em;color:#60a5fa;margin-bottom:15px}
.endpoint{display:flex;align-items:flex-start;justify-content:space-between;padding:12px 0;border-bottom:1px solid #1a1a1a}
.endpoint:last-child{border-bottom:none}
.method{font-weight:700;font-family:monospace;font-size:0.9em;min-width:200px}
.GET{color:#4ade80}.POST{color:#fbbf24}
.price{font-weight:600;font-size:0.85em}
.desc{color:#999;font-size:0.9em;margin-top:4px}
code{background:#1a1a1a;padding:2px 6px;border-radius:4px;font-size:0.9em;color:#a78bfa}
pre{background:#1a1a1a;padding:15px;border-radius:8px;overflow-x:auto;margin:10px 0}
pre code{background:none;padding:0;color:#e0e0e0}
a{color:#60a5fa;text-decoration:none}
a:hover{text-decoration:underline}
.footer{text-align:center;padding:30px;color:#555;font-size:0.85em}
.wallet{font-family:monospace;font-size:0.85em;color:#666}
</style>
</head>
<body>
<div class="container">
<header>
<h1>AgentServices</h1>
<p class="tagline">Paid APIs for AI Agents — Market Data + Dispute Resolution</p>
<div style="margin-top:10px">
<span class="badge badge-x402">x402 / USDC on Base</span>
<span class="badge badge-free">4 Free Endpoints</span>
<span class="badge badge-paid">4 Paid Endpoints</span>
</div>
</header>

<section>
<h2>Quick Start</h2>
<p>No signup. No API keys. Free endpoints work immediately. Paid endpoints use x402 micropayments.</p>
<pre><code># Free: Get BTC price
curl https://agentservices.to/v1/price/BTC

# Free: Batch prices
curl "https://agentservices.to/v1/prices?symbols=BTC,ETH,SOL"

# Free: Fear & Greed Index
curl https://agentservices.to/v1/fear-greed

# MCP: Connect your AI tool
# URL: https://agentservices.to/mcp (Streamable HTTP)</code></pre>
</section>

<section>
<h2>Market Data</h2>
<div class="endpoint">
<div><div class="method GET">GET /v1/price/{symbol}</div><div class="desc">Current crypto price (BTC, ETH, SOL, XRP...)</div></div>
<span class="badge badge-free">FREE</span>
</div>
<div class="endpoint">
<div><div class="method GET">GET /v1/prices?symbols=BTC,ETH</div><div class="desc">Batch crypto prices</div></div>
<span class="badge badge-free">FREE</span>
</div>
<div class="endpoint">
<div><div class="method GET">GET /v1/indicators/{symbol}</div><div class="desc">RSI, Bollinger Bands, ATR, Support/Resistance</div></div>
<span class="price">$0.02</span>
</div>
<div class="endpoint">
<div><div class="method GET">GET /v1/yields</div><div class="desc">Top DeFi yield pools by TVL</div></div>
<span class="price">$0.02</span>
</div>
<div class="endpoint">
<div><div class="method GET">GET /v1/fear-greed</div><div class="desc">Crypto Fear & Greed Index (0-100)</div></div>
<span class="badge badge-free">FREE</span>
</div>
</section>

<section>
<h2>Location & Web</h2>
<div class="endpoint">
<div><div class="method GET">GET /v1/geo/{ip}</div><div class="desc">IP geolocation lookup (country, city, ISP)</div></div>
<span class="badge badge-free">FREE</span>
</div>
<div class="endpoint">
<div><div class="method GET">GET /v1/metadata?url=...</div><div class="desc">URL metadata extraction and unfurling</div></div>
<span class="price">$0.01</span>
</div>
</section>

<section>
<h2>Dispute Resolution (AgentCourt Engine)</h2>
<div class="endpoint">
<div><div class="method POST">POST /v1/disputes</div><div class="desc">Submit dispute for policy-driven ruling. 7 policies: freelance, milestone, SLA, API quality, bug bounty, scope, physical commerce.</div></div>
<span class="price">$0.05</span>
</div>
<div class="endpoint">
<div><div class="method GET">GET /v1/policies</div><div class="desc">List dispute policy templates</div></div>
<span class="badge badge-free">FREE</span>
</div>
</section>

<section>
<h2>MCP Integration</h2>
<p>Connect AgentServices directly to Claude, Cursor, or any MCP client:</p>
<pre><code>MCP Server URL: https://agentservices.to/mcp
Transport: Streamable HTTP</code></pre>
<p>8 tools available immediately. No installation required.</p>
</section>

<section>
<h2>Payments (x402)</h2>
<p>Paid endpoints use the <a href="https://x402.org" target="_blank">x402 protocol</a>. No API keys, no subscriptions.</p>
<ol style="padding-left:20px;color:#999">
<li>Agent requests a paid endpoint</li>
<li>Server returns HTTP 402 with payment details</li>
<li>Agent pays in USDC on Base Mainnet</li>
<li>Server verifies and returns data</li>
</ol>
<p class="wallet">Wallet: 0x9863aB6242663FCc84c33632741711dB78f8Fd15</p>
</section>

<section>
<h2>Links</h2>
<p><a href="/docs">Swagger/OpenAPI Docs</a> · <a href="/llms.txt">llms.txt</a> · <a href="/health">Health Check</a> · <a href="https://github.com/vbkotecha/agentservices-api">GitHub</a></p>
</section>

<div class="footer">
<p>AgentServices — MIT License</p>
</div>
</div>
</body>
</html>
""")


# ============================================================
# NEW v5.0.0 ENDPOINTS — Synthesis + Inference Gateway
# ============================================================

# --- Inference Gateway (BlockRun competitor) ---

class InferenceRequest(BaseModel):
    model: str = Field(default="gpt-5.4-mini", description="gpt-5.4, gpt-5.4-mini, or gpt-5.5")
    messages: List[dict] = Field(description="Chat messages in OpenAI format [{role, content}]")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1, le=16000)

@app.get("/v1/models", tags=["Inference"])
async def list_models():
    """List available inference models (FREE)"""
    return list_inference_models()

@app.post("/v1/inference", tags=["Inference"],
          summary="LLM Inference — Chat Completion",
          description="Send a chat completion request. Models: gpt-5.4, gpt-5.4-mini, gpt-5.5. Costs $0.03 USDC via x402.")
async def llm_inference(req: InferenceRequest):
    """LLM inference gateway ($0.03 per call via x402)"""
    return inference(
        model=req.model,
        messages=req.messages,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
    )

@app.post("/v1/complete", tags=["Inference"],
          summary="Quick Text Completion",
          description="Send a prompt, get a completion. Simpler than /v1/inference. Costs $0.03 USDC via x402.")
async def quick_completion(prompt: str, model: str = "auto", max_tokens: int = 500):
    """Quick text completion ($0.03 per call via x402)"""
    return quick_complete(prompt=prompt, model=model, max_tokens=max_tokens)


# --- OpenAI-Compatible Chat Completions (400+ models) ---

class ChatCompletionRequest(BaseModel):
    model: str = Field(default="auto", description="Model ID or 'auto' for smart routing. 400+ models available.")
    messages: List[dict] = Field(description="Chat messages in OpenAI format [{role, content}]")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1, le=4096)
    stream: bool = Field(default=False)
    profile: str = Field(default="auto", description="Router profile: auto, eco, premium, free")

@app.post("/v1/chat/completions", tags=["Inference"],
          summary="Chat Completions (OpenAI-compatible, 400+ models)",
          description="Drop-in OpenAI replacement. 400+ models via OpenRouter. Dynamic pricing: provider cost + 5%, floor $0.003. Use model='auto' for smart routing.")
async def chat_completions_endpoint(req: ChatCompletionRequest):
    """OpenAI-compatible chat completions — dynamic pricing via x402"""
    return chat_completions(
        model=req.model,
        messages=req.messages,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        profile=req.profile,
    )

@app.get("/v1/models/all", tags=["Inference"],
         summary="List All Available Models",
         description="Fetch the complete live model list from OpenRouter (400+ models). FREE.")
async def all_models():
    """Full live model catalog from OpenRouter (FREE)"""
    return list_all_openrouter_models()


# --- Media Generation ---

class ImageRequest(BaseModel):
    prompt: str = Field(description="Image description")
    size: str = Field(default="1024x1024", description="256x256, 512x512, or 1024x1024")
    model: str = Field(default="gpt-image-2")

@app.post("/v1/images/generations", tags=["Media"],
          summary="AI Image Generation",
          description="Generate an image from a text prompt. $0.05 USDC via x402.")
async def image_generation(req: ImageRequest):
    """AI image generation ($0.05 per image via x402)"""
    return generate_image(prompt=req.prompt, size=req.size, model=req.model)

class TTSRequest(BaseModel):
    text: str = Field(description="Text to convert to speech")
    voice: str = Field(default="alloy", description="Voice: alloy, echo, fable, onyx, nova, shimmer")
    model: str = Field(default="openai/gpt-audio-mini")

@app.post("/v1/audio/speech", tags=["Media"],
          summary="Text-to-Speech",
          description="Convert text to speech audio. $0.05 USDC via x402.")
async def tts_endpoint(req: TTSRequest):
    """Text-to-speech ($0.05 per call via x402)"""
    return text_to_speech(text=req.text, model=req.model, voice=req.voice)


# --- Synthesis Endpoints ---

@app.get("/v1/token-risk/{token}", tags=["Synthesis"],
         summary="Token Risk Scoring",
         description="Risk score (0-100) for any crypto token. Analyzes volatility, liquidity, and market cap. Costs $0.03 USDC via x402.")
async def token_risk(token: str):
    """Token risk scoring ($0.03 per call via x402)"""
    return get_token_risk(token)

@app.get("/v1/signals/{symbol}", tags=["Synthesis"],
         summary="Crypto Buy/Sell Signals",
         description="Synthesized trading signal from RSI, moving averages, and Bollinger Bands. Costs $0.04 USDC via x402.")
async def crypto_signals(symbol: str):
    """Crypto signal feed ($0.04 per call via x402)"""
    return get_crypto_signal(symbol)

@app.get("/v1/hn-sentiment", tags=["Synthesis"],
         summary="Hacker News Sentiment",
         description="Tech sentiment from top HN stories. Optionally filter by query. Costs $0.02 USDC via x402.")
async def hn_sentiment(query: str = ""):
    """Hacker News sentiment ($0.02 per call via x402)"""
    return get_hn_sentiment(query)

@app.get("/v1/npm-stats/{package}", tags=["Synthesis"],
         summary="NPM Download Stats",
         description="Package download statistics and trend analysis. Costs $0.02 USDC via x402.")
async def npm_stats(package: str):
    """NPM package stats ($0.02 per call via x402)"""
    return get_npm_stats(package)

@app.get("/v1/github-trending", tags=["Synthesis"],
         summary="GitHub Trending Repos",
         description="Hot repositories created in the last 7 days. Filter by language. Costs $0.02 USDC via x402.")
async def github_trending(language: str = "", since: str = "daily"):
    """GitHub trending ($0.02 per call via x402)"""
    return get_github_trending(language, since)

@app.get("/v1/yield-comparison", tags=["Synthesis"],
         summary="DeFi Yield Comparison with Risk",
         description="Compare DeFi yields with risk-adjusted analysis. Not just raw APY. Costs $0.03 USDC via x402.")
async def yield_comparison(chain: str = ""):
    """Risk-adjusted yield comparison ($0.03 per call via x402)"""
    return get_yield_comparison(chain)


# ============================================================
# TRADITIONAL FINANCE ENDPOINTS (v5.1.0 — Gap Fillers)
# ============================================================

@app.get("/v1/stocks/{ticker}", tags=["Traditional Finance"],
         summary="Stock Market Quote",
         description="Real-time stock quote from Yahoo Finance. Only 2 providers on Bazaar. $0.02 USDC via x402.")
async def stock_quote(ticker: str):
    """Stock quote ($0.02 per call via x402)"""
    return get_stock_quote(ticker)

@app.get("/v1/stocks/{ticker}/history", tags=["Traditional Finance"],
         summary="Historical Stock Data",
         description="Historical OHLCV data. Range: 1d, 5d, 1mo, 3mo, 6mo, 1y, 5y. $0.03 USDC via x402.")
async def stock_history(ticker: str, range: str = "3mo"):
    """Historical stock OHLCV ($0.03 per call via x402)"""
    return get_stock_history(ticker, range)

@app.get("/v1/sec/{ticker}", tags=["Traditional Finance"],
         summary="SEC Filings Parser",
         description="Recent SEC filings (10-K, 10-Q, 8-K, Form 4) from EDGAR. Only 2 providers on Bazaar. $0.03 USDC via x402.")
async def sec_filings(ticker: str, filing_type: str = "10-K"):
    """SEC filings ($0.03 per call via x402)"""
    return get_sec_filings(ticker, filing_type)

@app.get("/v1/commodities", tags=["Traditional Finance"],
         summary="Commodity Prices",
         description="Oil, gold, silver, copper, wheat, corn, coffee, and more. Undercuts LoneStar ($0.05). $0.03 USDC via x402.")
async def commodities(category: str = "all"):
    """Commodity prices ($0.03 per call via x402)"""
    return get_commodities()

@app.get("/v1/economic", tags=["Traditional Finance"],
         summary="Economic Indicators",
         description="CPI, GDP, unemployment, Fed funds rate, Treasury yields. From FRED. $0.03 USDC via x402.")
async def economic_indicators(indicator: str = "all"):
    """US economic indicators ($0.03 per call via x402)"""
    return get_economic_indicators()

@app.get("/v1/fx", tags=["Traditional Finance"],
         summary="FX / Forex Rates",
         description="Real-time exchange rates for 30+ currencies. Only 1 provider on Bazaar. $0.003 USDC via x402.")
async def fx_rates(base: str = "USD"):
    """FX rates ($0.003 per call via x402)"""
    return get_fx_rates(base)


@app.get("/v1/fx-rates", tags=["Traditional Finance"],
         summary="FX / Forex Rates (alias)",
         description="Alias for /v1/fx. Real-time exchange rates for 30+ currencies. $0.003 USDC via x402.",
         include_in_schema=False)
async def fx_rates_alias(base: str = "USD"):
    """FX rates alias ($0.003 per call via x402)"""
    return get_fx_rates(base)


@app.get("/v1/gov/us/ca/entity", tags=["Government"],
         summary="California Business Entity Status",
         description="Public California SOS business entity lookup by name or entity number. SKU ca.entity.status. $0.03 USDC via x402.")
async def ca_entity_status(q: str = Query(..., description="Business name or California entity number")):
    """California entity status ($0.03 per call via x402)"""
    return get_ca_entity_status(q)


# ============================================================
# UTILITY ENDPOINTS (v5.1.0 — Gap Fillers)
# ============================================================

@app.get("/v1/extract", tags=["Utility"],
         summary="Web Content Extraction",
         description="Fetch any URL and get clean, token-efficient text. Strips ads, nav, scripts. $0.002 USDC via x402.")
async def web_extract(url: str):
    """Web content extraction ($0.002 per call via x402)"""
    return extract_web_content(url)

@app.get("/v1/security/{package}", tags=["Utility"],
         summary="Package Security Scan",
         description="Check PyPI/npm packages for known vulnerabilities. Only 1 provider on Bazaar. $0.02 USDC via x402.")
async def package_security(package: str, ecosystem: str = "PyPI"):
    """Package security scan ($0.02 per call via x402)"""
    return scan_package_security(package, ecosystem)

@app.get("/v1/seo/keywords", tags=["Utility"],
         summary="SEO Keyword Research",
         description="Keyword research with volume estimates and competition data. SpyFu has 46 endpoints — proven demand. $0.01 USDC via x402.")
async def keyword_research(keyword: str):
    """SEO keyword research ($0.01 per call via x402)"""
    return seo_keywords(keyword)

@app.get("/v1/backlinks", tags=["Utility"],
         summary="Backlink Intelligence",
         description="Backlinks — deduplicated URL list with unique referring domains, capped at 1,000 URLs. $0.02 USDC via x402.")
async def backlink_research(domain: str, site_url: str | None = None):
    """Backlink intelligence ($0.02 per call via x402)."""
    return backlink_intelligence(domain, site_url)


# --- Deep Research (Flagship Bundled Endpoint) ---

@app.get("/v1/research", tags=["Research"],
         summary="Deep Research — Search + Extract + Synthesize",
         description="One-call deep research: searches the web, extracts content from top sources, and synthesizes an intelligence brief with key findings, themes, and sentiment. Replaces 3+ separate API calls. $0.05 USDC via x402.")
async def research_endpoint(q: str, sources: int = 3):
    """
    Deep Research ($0.05 per call via x402)

    Bundles: web search + content extraction + synthesis analysis.
    Returns a structured intelligence brief with key findings, themes, and sentiment.
    """
    return deep_research(q, max_sources=min(sources, 5))


# --- Portfolio Intelligence (High-Value Bundled Endpoint) ---

@app.get("/v1/portfolio", tags=["Intelligence"],
         summary="Portfolio Intelligence — Price + Signal + Risk + Sentiment",
         description="Comprehensive asset analysis in one call: market data, technical signals (RSI, MA, Bollinger), risk scoring, and market sentiment (Fear & Greed). Replaces 4+ separate API calls. $0.10 USDC via x402.")
async def portfolio_endpoint(symbol: str):
    """
    Portfolio Intelligence ($0.10 per call via x402)

    Bundles: price + technical signal + risk score + market sentiment.
    Returns a synthesized verdict combining all modules.
    """
    return portfolio_intelligence(symbol)


# --- DeFi Strategy Report (High-Value Bundled Endpoint) ---

@app.get("/v1/defi-strategy", tags=["Intelligence"],
         summary="DeFi Strategy — Yields + TVL + Comparison + Risk",
         description="Comprehensive DeFi investment analysis: top yield opportunities, protocol TVL rankings, cross-chain yield comparison, and risk assessment with high-APY flags. Replaces 4+ API calls. $0.25 USDC via x402.")
async def defi_strategy_endpoint(chain: str = ""):
    """
    DeFi Strategy Report ($0.25 per call via x402)

    Bundles: yield opportunities + protocol TVL + yield comparison + risk flags.
    Returns synthesized investment strategy with risk-adjusted recommendations.
    """
    return defi_strategy_report(chain)


# --- Market Pulse (Rapid Market Snapshot) ---

@app.get("/v1/market-pulse", tags=["Intelligence"],
         summary="Market Pulse — Sentiment + Trending + News + Whales",
         description="Real-time crypto market snapshot: Fear & Greed index, trending tokens, latest news, social signals, whale movements, and global market stats. Replaces 6+ API calls. $0.05 USDC via x402.")
async def market_pulse_endpoint(
    depth: str = Query("full", description="Detail level: 'summary' for key signals only, 'full' for complete data"),
    currency: str = Query("usd", description="Currency for market cap and price denominations")
):
    """
    Market Pulse ($0.05 per call via x402)

    Bundles: sentiment + trending + news + social + whales + global market.
    Returns synthesized market direction signal for rapid agent decision-making.
    """
    return market_pulse()


@app.get("/v1/onchain-overview", tags=["Intelligence"],
         summary="On-Chain Overview — Whales + Flows + Correlation + TVL",
         description="Comprehensive on-chain intelligence: whale movements, exchange flows, stablecoin flows, correlation matrix, and DeFi TVL in one call. Replaces 5+ API calls. $0.15 USDC via x402.")
async def onchain_overview_endpoint(
    depth: str = Query("full", description="Detail level: 'summary' for key signals only, 'full' for complete data"),
    chain: str = Query("all", description="Blockchain filter: 'ethereum', 'base', 'arbitrum', 'solana', or 'all'")
):
    """
    On-Chain Overview ($0.15 per call via x402)

    Bundles: whale activity + exchange flows + stablecoin flows + correlation matrix + DeFi TVL.
    Returns synthesized on-chain assessment for smart money tracking and liquidity flow analysis.
    """
    return onchain_overview()


# --- Cross-DEX Arbitrage Scanner ---

@app.get("/v1/arbitrage", tags=["Intelligence"],
         summary="Arbitrage Scanner — Cross-DEX Price Discrepancies + Profitability",
         description="Cross-DEX arbitrage scanner: compares token prices across exchanges, calculates gas-adjusted profitability, models slippage, and flags actionable opportunities. Unique computation — no free API provides this. $0.08 USDC via x402.")
async def arbitrage_scanner_endpoint(symbols: str = "BTC,ETH,SOL,USDC,WETH,WBTC"):
    """
    Cross-DEX Arbitrage Scanner ($0.08 per call via x402)

    Scans for price discrepancies across exchanges. For each symbol:
    - Compares prices from CoinGecko (aggregated) vs Coinbase spot
    - Calculates spread percentage and absolute
    - Models profitability at $100/$1K/$10K/$100K trade sizes
    - Factors in gas costs (Base L2) and slippage proportional to volume
    - Flags opportunities where net ROI > 0.5% after costs

    This is COMPUTATION, not data fetching. Addresses competitive feedback
    that raw data endpoints are commoditized.
    """
    return arbitrage_scanner(symbols)


# --- DeFi Liquidation Map (High-Value Risk Computation) ---

@app.get("/v1/liquidation-map", tags=["Intelligence"],
         summary="Liquidation Map — DeFi Positions Near Liquidation + Cascading Risk",
         description="DeFi liquidation heatmap: calculates liquidation prices across Aave V3, Compound V3, and MakerDAO for any token. Models cascading liquidation risk, estimates volume at risk, and flags critical price zones. Unique computation — no free API provides this. $0.12 USDC via x402.")
async def liquidation_map_endpoint(symbols: str = "BTC,ETH,LINK,AAVE,UNI"):
    """
    DeFi Liquidation Map ($0.12 per call via x402)

    Computes liquidation thresholds across 3 major lending protocols.
    For each token: liquidation prices at different leverage levels,
    estimated volume at risk, and cascading liquidation probability.
    """
    return liquidation_map(symbols)


# --- Agent-Friendly Examples Page ---

_examples_html = None
def _get_examples():
    global _examples_html
    if _examples_html is None:
        _examples_html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AgentServices — Agent Integration Examples</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'SF Mono','Fira Code',monospace;background:#0a0a0a;color:#e0e0e0;line-height:1.6;padding:20px}
.container{max-width:900px;margin:0 auto}
h1{color:#fff;font-size:1.8em;margin-bottom:10px}
h1 a{color:#4A90D9;text-decoration:none}
.subtitle{color:#888;margin-bottom:30px;font-size:0.95em}
h2{color:#4A90D9;font-size:1.2em;margin:30px 0 12px;border-bottom:1px solid #222;padding-bottom:6px}
h3{color:#e8e8e8;font-size:1em;margin:20px 0 8px}
.section{background:#111;border-radius:8px;padding:20px;margin-bottom:20px;border:1px solid #1a1a1a}
.code-block{background:#0d0d0d;border:1px solid #1a1a1a;border-radius:6px;padding:14px;overflow-x:auto;margin:8px 0;font-size:0.85em;color:#a8ffa8}
.code-block .comment{color:#666}
.code-block .var{color:#4A90D9}
.badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:0.75em;font-weight:bold;margin-left:8px}
.badge-free{background:#1a3a1a;color:#4ade80}
.badge-paid{background:#3a2a1a;color:#fbbf24}
.badge-bundle{background:#2a1a3a;color:#a78bfa}
.tag{display:inline-block;background:#1a1a2e;color:#6b7afe;padding:2px 8px;border-radius:3px;font-size:0.75em;margin:2px}
.note{color:#888;font-size:0.85em;font-style:italic;margin:5px 0}
a{color:#4A90D9}
</style>
</head>
<body>
<div class="container">
<h1>🔗 <a href="/">AgentServices</a> — Agent Integration Examples</h1>
<p class="subtitle">Ready-to-use prompts and commands for AI agents. Copy, paste, execute.</p>

<div class="section">
<h2>Quick Start for AI Agents</h2>
<p>AgentServices provides 50+ APIs for AI agents. Free endpoints work immediately. Paid endpoints use x402 (USDC micropayments on Base).</p>
<p style="margin-top:8px">
<span class="tag">x402</span>
<span class="tag">USDC</span>
<span class="tag">Base Mainnet</span>
<span class="tag">MCP</span>
<span class="tag">OpenAPI 3.1</span>
</p>
</div>

<div class="section">
<h2>1. Free Endpoints — No Payment Needed</h2>
<h3>Crypto Prices</h3>
<div class="code-block"><span class="comment"># Get current price for any crypto</span>
curl https://agentservices.to/v1/prices?symbols=BTC,ETH,SOL

<span class="comment"># Single asset</span>
curl https://agentservices.to/v1/price/BTC</div>

<h3>Market Overview</h3>
<div class="code-block"><span class="comment"># Global market stats</span>
curl https://agentservices.to/v1/global

<span class="comment"># Fear & Greed Index</span>
curl https://agentservices.to/v1/fear-greed

<span class="comment"># Trending tokens</span>
curl https://agentservices.to/v1/trending

<span class="comment"># Latest crypto news</span>
curl https://agentservices.to/v1/news</div>

<h3>Agent-Ready Context</h3>
<div class="code-block"><span class="comment"># Paste-ready market context for LLMs</span>
curl https://agentservices.to/v1/agent-context</div>
</div>

<div class="section">
<h2>2. MCP Integration — Connect to Claude, Cursor, or Any MCP Client</h2>
<p>AgentServices exposes a remote MCP server at <code>/mcp</code>. No installation required.</p>
<div class="code-block"><span class="comment"># Claude Desktop / Cursor config (add to mcp.json)</span>
{
  "mcpServers": {
    "agentservices": {
      "url": "https://agentservices.to/mcp"
    }
  }
}

<span class="comment"># List available MCP tools</span>
curl https://agentservices.to/mcp/tools</div>
<p class="note">36 MCP tools available — crypto data, market intelligence, search, DeFi, on-chain analytics, and more.</p>
</div>

<div class="section">
<h2>3. Paid Endpoints — x402 Payments <span class="badge badge-paid">$0.01-$0.25</span></h2>
<p>Paid endpoints return HTTP 402 with payment instructions. Use any x402-compatible wallet.</p>

<h3>Web Search <span class="badge badge-paid">$0.01</span></h3>
<div class="code-block"><span class="comment"># AI-powered web search</span>
curl https://agentservices.to/v1/search?q=latest+AI+agent+frameworks

<span class="comment"># Returns 402 → pay with x402 wallet → get results</span></div>

<h3>Technical Indicators <span class="badge badge-paid">$0.02</span></h3>
<div class="code-block">curl https://agentservices.to/v1/indicators/BTC
<span class="comment"># RSI, Bollinger Bands, ATR, Support/Resistance</span></div>

<h3>DeFi Yields <span class="badge badge-paid">$0.02</span></h3>
<div class="code-block">curl https://agentservices.to/v1/yields
<span class="comment"># Top yield pools by TVL across chains</span></div>
</div>

<div class="section">
<h2>4. Bundled Intelligence — One Call, Full Analysis <span class="badge badge-bundle">BEST VALUE</span></h2>
<p>Aggregated endpoints that replace multiple API calls. Higher value, lower total cost.</p>

<h3>Deep Research <span class="badge badge-bundle">$0.05</span></h3>
<div class="code-block"><span class="comment"># Search + Extract + Synthesize in one call</span>
curl "https://agentservices.to/v1/research?q=ethereum+merge+impact+on+defi"</div>

<h3>Portfolio Intelligence <span class="badge badge-bundle">$0.10</span></h3>
<div class="code-block"><span class="comment"># Price + Signal + Risk + Sentiment + Verdict</span>
curl "https://agentservices.to/v1/portfolio?symbol=BTC"</div>

<h3>Market Pulse <span class="badge badge-bundle">$0.05</span></h3>
<div class="code-block"><span class="comment"># Sentiment + Trending + News + Whales + Global snapshot</span>
curl https://agentservices.to/v1/market-pulse</div>

<h3>DeFi Strategy Report <span class="badge badge-bundle">$0.25</span></h3>
<div class="code-block"><span class="comment"># Yields + TVL + Cross-chain comparison + Risk assessment</span>
curl "https://agentservices.to/v1/defi-strategy?chain=ethereum"</div>

<h3>On-Chain Overview <span class="badge badge-bundle">$0.15</span></h3>
<div class="code-block"><span class="comment"># Whales + Exchange flows + Stablecoin flows + Correlation + DeFi TVL</span>
curl https://agentservices.to/v1/onchain-overview</div>
</div>

<div class="section">
<h2>5. LLM Inference Gateway <span class="badge badge-paid">$0.03</span></h3>
<div class="code-block"><span class="comment"># List models</span>
curl https://agentservices.to/v1/models

<span class="comment"># Chat completion (OpenAI-compatible)</span>
curl -X POST https://agentservices.to/v1/inference \\
  -H "Content-Type: application/json" \\
  -d '{"model":"gpt-5.4-mini","messages":[{"role":"user","content":"What is DeFi?"}]}'</div>
</div>

<div class="section">
<h2>6. Use-Case: Portfolio Monitoring Agent</h2>
<div class="code-block"><span class="comment"># Step 1: Get free prices</span>
curl "https://agentservices.to/v1/prices?symbols=BTC,ETH,LINK"

<span class="comment"># Step 2: Get technical signals ($0.02)</span>
curl https://agentservices.to/v1/indicators/BTC

<span class="comment"># Step 3: Get full portfolio intelligence ($0.10)</span>
curl "https://agentservices.to/v1/portfolio?symbol=ETH"

<span class="comment"># Total cost for full portfolio check: ~$0.14</span></div>
</div>

<div class="section">
<h2>7. Use-Case: Market Intelligence Agent</h2>
<div class="code-block"><span class="comment"># Step 1: Market pulse ($0.05) — full snapshot</span>
curl https://agentservices.to/v1/market-pulse

<span class="comment"># Step 2: Deep research on a topic ($0.05)</span>
curl "https://agentservices.to/v1/research?q=base+chain+ecosystem+growth+2026"

<span class="comment"># Step 3: On-chain overview ($0.15) — smart money flows</span>
curl https://agentservices.to/v1/onchain-overview

<span class="comment"># Total cost for full market intelligence: ~$0.25</span></div>
</div>

<div class="section">
<h2>8. Discovery Manifests</h2>
<div class="code-block"><span class="comment"># x402 payment manifest</span>
curl https://agentservices.to/.well-known/x402

<span class="comment"># OpenAPI 3.1 spec</span>
curl https://agentservices.to/openapi.json

<span class="comment"># Agent skills manifest</span>
curl https://agentservices.to/.well-known/agentskills/agentservices/SKILL.md

<span class="comment"># MCP server card</span>
curl https://agentservices.to/.well-known/mcp/server-card.json

<span class="comment"># llms.txt for LLM crawlers</span>
curl https://agentservices.to/llms.txt</div>
</div>

<div class="section">
<h2>9. x402 Payment Flow</h2>
<p>All paid endpoints use the x402 protocol. When you hit a paid endpoint:</p>
<div class="code-block"><span class="comment"># 1. Agent sends GET request</span>
curl https://agentservices.to/v1/search?q=base+chain

<span class="comment"># 2. Server responds with 402 Payment Required:</span>
<span class="comment"># {</span>
<span class="comment">#   "x402Version": 2,</span>
<span class="comment">#   "accepts": {</span>
<span class="comment">#     "url": "https://agentservices.to/v1/search?q=base+chain",</span>
<span class="comment">#     "maxAmountRequired": 1000,</span>
<span class="comment">#     "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",</span>
<span class="comment">#     "network": "eip155:8453"</span>
<span class="comment">#   }</span>
<span class="comment"># }</span>

<span class="comment"># 3. Agent pays via x402 wallet (CDP, Coinbase Smart Wallet, etc.)</span>
<span class="comment"># 4. Server returns data with payment receipt</span></div>
<p class="note">Network: Base Mainnet (Chain ID 8453). Asset: USDC. Facilitator: CDP.</p>
</div>

<div class="section" style="text-align:center">
<p>
<a href="/">← Back to AgentServices</a> | 
<a href="/docs">API Docs</a> | 
<a href="/openapi.json">OpenAPI Spec</a> | 
<a href="https://github.com/vbkotecha/agentservices-api">GitHub</a>
</p>
<p style="margin-top:8px;color:#555;font-size:0.8em">
AgentServices — Paid APIs for AI agents. 53 services. x402/USDC on Base.
</p>
</div>

</div>
</body>
</html>"""
    return _examples_html


@app.get("/index.md", include_in_schema=False)
async def index_markdown():
    """Serve landing page content as markdown for AI crawlers."""
    from starlette.responses import PlainTextResponse
    return PlainTextResponse(content=_get_llms_full_markdown(), media_type="text/markdown")


@app.get("/examples", tags=["Developer"], response_class=HTMLResponse)
async def examples_page():
    """Agent-friendly examples page with ready-to-use prompts and curl commands."""
    return HTMLResponse(content=_get_examples())


# ============================================================
# AGENT MEMORY (v5.2.0 — Retention Hook)
# ============================================================

class MemoryRequest(BaseModel):
    value: str = Field(description="Value to store")
    ttl_seconds: int = Field(default=0, description="TTL in seconds (0 = permanent)")

@app.post("/v1/memory/{key}", tags=["Agent Memory"],
          summary="Store Agent Memory",
          description="Store a value keyed to the caller's wallet. Persistent across sessions. $0.01 via x402.")
async def memory_store(key: str, req: MemoryRequest, request: Request):
    """Store agent memory ($0.01 via x402)"""
    wallet = request.headers.get("x-payment-payer", request.client.host)
    return mem_store(wallet, key, req.value, req.ttl_seconds)

@app.get("/v1/memory/{key}", tags=["Agent Memory"],
          summary="Retrieve Agent Memory",
          description="Retrieve a stored value by key. $0.01 via x402.")
async def memory_get(key: str, request: Request):
    """Retrieve agent memory ($0.01 via x402)"""
    wallet = request.headers.get("x-payment-payer", request.client.host)
    return mem_retrieve(wallet, key)

@app.delete("/v1/memory/{key}", tags=["Agent Memory"],
          summary="Delete Agent Memory",
          description="Delete a stored value. $0.01 via x402.")
async def memory_del(key: str, request: Request):
    """Delete agent memory ($0.01 via x402)"""
    wallet = request.headers.get("x-payment-payer", request.client.host)
    return mem_delete(wallet, key)

@app.get("/v1/memory", tags=["Agent Memory"],
          summary="List Agent Memory Keys",
          description="List all stored keys for the caller's wallet. $0.01 via x402.")
async def memory_list(request: Request):
    """List agent memory keys ($0.01 via x402)"""
    wallet = request.headers.get("x-payment-payer", request.client.host)
    return mem_list(wallet)

class MemorySearchRequest(BaseModel):
    query: str = Field(description="Search query")

@app.post("/v1/memory/search", tags=["Agent Memory"],
          summary="Search Agent Memory",
          description="Semantic search across all stored values. $0.02 via x402.")
async def memory_search_endpoint(req: MemorySearchRequest, request: Request):
    """Search agent memory ($0.02 via x402)"""
    wallet = request.headers.get("x-payment-payer", request.client.host)
    return mem_search(wallet, req.query)


# ============================================================
# SKILL PACKS (v5.2.0 — Bundled Intelligence)
# ============================================================

class SkillRequest(BaseModel):
    symbol: str = Field(default="", description="Crypto symbol or stock ticker")

@app.get("/v1/skills", tags=["Skill Packs"],
          summary="List Available Skills",
          description="List all available skill packs (bundled multi-endpoint intelligence). FREE.")
async def skills_list():
    """List available skills (FREE)"""
    return available_skills()

@app.post("/v1/skills/crypto-dossier", tags=["Skill Packs"],
          summary="Crypto Dossier",
          description="Full crypto intelligence in one call: price + indicators + risk + signal + fear/greed + whales. $0.10 via x402.")
async def skill_crypto(req: SkillRequest):
    """Crypto dossier ($0.10 via x402)"""
    return crypto_dossier(req.symbol)

@app.post("/v1/skills/stock-dossier", tags=["Skill Packs"],
          summary="Stock Dossier",
          description="Full stock intelligence: quote + FX + sentiment. $0.05 via x402.")
async def skill_stock(req: SkillRequest):
    """Stock dossier ($0.05 via x402)"""
    return stock_dossier(req.symbol)

@app.get("/v1/skills/market-overview", tags=["Skill Packs"],
          summary="Market Overview",
          description="Full market pulse: fear/greed + BTC signal + whales + regime classification. $0.05 via x402.")
async def skill_market(
    depth: str = Query("full", description="Detail level: 'summary' for key signals, 'full' for complete dataset")
):
    """Market overview ($0.05 via x402)"""
    return market_overview()


# --- Privacy Policy (required for Anthropic Connector Directory) ---
@app.get("/privacy", tags=["Legal"], summary="Privacy Policy")
async def privacy_policy():
    """AgentServices Privacy Policy — required for MCP directory submissions."""
    return {
        "policy_version": "1.0",
        "last_updated": "2026-07-08",
        "data_collection": {
            "what_we_collect": [
                "API request parameters (e.g., crypto symbols, URLs, IP addresses provided by caller)",
                "Payment metadata from x402 protocol (transaction hashes, wallet addresses)",
                "Standard HTTP request headers (User-Agent, Accept, Content-Type)",
                "Timestamp and endpoint path for rate limiting and analytics"
            ],
            "what_we_do_not_collect": [
                "Personal names, emails, phone numbers",
                "Browser cookies or tracking pixels",
                "Location data beyond what the caller explicitly provides",
                "Biometric or identity data"
            ]
        },
        "data_usage": {
            "purpose": "All collected data is used solely for processing API requests and returning responses. Payment metadata is used for x402 protocol verification only.",
            "retention": "Request logs are retained for 30 days for debugging and rate limiting, then automatically purged. Payment metadata is retained per on-chain immutability (we do not store it separately).",
            "sharing": "We do not sell, share, or transfer data to third parties. Data is processed in-memory for request fulfillment and discarded."
        },
        "security": {
            "transport": "All communication uses HTTPS/TLS 1.2+",
            "authentication": "Free endpoints require no authentication. Paid endpoints use x402 (HTTP 402) payment protocol with USDC on Base blockchain. No passwords or OAuth tokens are collected.",
            "infrastructure": "Hosted on Railway (SOC 2 Type II certified infrastructure provider). No on-disk persistent storage of request data."
        },
        "user_rights": {
            "data_access": "Users can access their request history via API logs (available on request)",
            "data_deletion": "Request data is automatically purged after 30 days. Users can request immediate deletion by contacting support.",
            "opt_out": "Users can stop using the service at any time. No accounts or subscriptions to cancel."
        },
        "contact": "For privacy inquiries: hustlemode@agentmail.to",
        "mcp_specific": {
            "origin_validation": "The MCP server validates Origin headers for enhanced security in Claude environments.",
            "no_user_data_modification": "All tools are read-only (readOnlyHint: true). AgentServices does not modify files, settings, or data on the user's system.",
            "external_calls": "Tools call AgentServices' own first-party APIs. No third-party API calls are made on behalf of the user."
        }
    }


@app.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource():
    """OAuth Protected Resource metadata (RFC 9728).
    Declares that our MCP server uses no authentication for free tools.
    Required for Anthropic Connector Directory compliance."""
    return {
        "resource": "https://agentservices.to/mcp",
        "authorization_servers": [],
        "bearer_methods_supported": [],
        "resource_documentation": "https://agentservices.to/docs",
        "resource_name": "AgentServices MCP Server",
        "resource_description": "Free tools require no auth. Paid tools use x402 (HTTP 402) payment. No OAuth required for discovery or free tool access.",
    }


@app.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server():
    """OAuth Authorization Server metadata.
    AgentServices does not operate an OAuth server — free tools are public, paid tools use x402."""
    return {
        "issuer": "https://agentservices.to",
        "authorization_endpoint": None,
        "token_endpoint": None,
        "response_types_supported": [],
        "grant_types_supported": [],
        "note": "AgentServices does not use OAuth. Free tools are publicly accessible. Paid tools use x402 micropayments (HTTP 402).",
    }


# --- llms.txt (agent-accessible documentation index) ---
@app.get("/llms.txt", tags=["Discovery"],
         summary="LLM-readable service index",
         response_class=PlainTextResponse)
@app.get("/.well-known/llms.txt", tags=["Discovery"],
         summary="LLM-readable service index (well-known)",
         include_in_schema=False,
         response_class=PlainTextResponse)
async def llms_txt():
    """Canonical index for AI agents and LLM crawlers. Follows the llms.txt convention."""
    from starlette.responses import PlainTextResponse
    live = _live_capability_summary()
    return PlainTextResponse(content=f"""# AgentServices

> Paid APIs for AI agents. {live['path_count']} live routes generated from the deployed OpenAPI schema. Data, search, market intelligence, inference, and ERC-8004 identity/reputation/evidence. Agents pay per call via x402 (USDC on Base).

## Quick Start
- Free endpoints: GET https://agentservices.to/v1/prices (crypto prices), GET https://agentservices.to/v1/fear-greed (market sentiment)
- Paid endpoints: GET https://agentservices.to/v1/indicators/BTC (0.02 USDC), GET https://agentservices.to/v1/search?q=... (0.01 USDC)
- MCP server: https://agentservices.to/mcp (37 tools, Streamable HTTP)
- Full docs: https://agentservices.to/docs
- OpenAPI spec: https://agentservices.to/openapi.json
- Health check: https://agentservices.to/health
- Task catalog: https://agentservices.to/v1/catalog/search?query=web+research
- Tool contract: https://agentservices.to/v1/catalog/tools/research.web
- Live capability schema: https://agentservices.to/openapi.json
- ERC-8004 provider metadata: https://agentservices.to/v1/erc8004/provider
- ERC-8004 agent discovery: https://agentservices.to/v1/erc8004/agents

## Key Endpoints
- [Crypto Prices](https://agentservices.to/v1/prices): Free. Real-time prices for 1000+ tokens.
- [Technical Indicators](https://agentservices.to/v1/indicators/BTC): $0.02. RSI, MACD, Bollinger, ATR, volume analysis.
- [DeFi Yields](https://agentservices.to/v1/yields): $0.02. Yield farming opportunities across protocols.
- [Search](https://agentservices.to/v1/search): $0.01. Web search with structured extraction.
- [Market Pulse](https://agentservices.to/v1/market-pulse): $0.05. Sentiment + trending + news + whales in one call.
- [On-Chain Overview](https://agentservices.to/v1/onchain-overview): $0.15. Whales + flows + correlation + TVL.
- [Portfolio Intelligence](https://agentservices.to/v1/portfolio): $0.10. Price + signal + risk + sentiment bundled.
- [DeFi Strategy](https://agentservices.to/v1/defi-strategy): $0.25. Full strategy report with recommendations.

## Payment
- Protocol: x402 (HTTP 402 Payment Required)
- Asset: USDC on Base (eip155:8453)
- Wallet: 0x9863aB6242663FCc84c33632741711dB78f8Fd15
- No API keys, no accounts, no subscriptions

## Integration
- MCP: Add https://agentservices.to/mcp to your MCP client
- Python SDK: pip install agentservices
- npm: npx agentservices-mcp
""", media_type="text/plain")


# --- agents.txt (agent instructions) ---
@app.get("/agents.txt", tags=["Discovery"],
         summary="Agent instructions file",
         response_class=PlainTextResponse)
async def agents_txt():
    """Instructions for AI agents crawling or using AgentServices."""
    from starlette.responses import PlainTextResponse
    live = _live_capability_summary()
    return PlainTextResponse(content=f"""# AgentServices — Agent Instructions

## What This Service Does
AgentServices provides paid API endpoints for AI agents. The deployed schema currently exposes {live['path_count']} routes covering crypto market data, on-chain analytics, DeFi intelligence, market sentiment, stock data, web extraction, AI inference, and ERC-8004 identity/reputation/evidence.

## How to Pay
1. Make a GET/POST request to any paid endpoint
2. Server responds with HTTP 402 + payment details (x402 protocol)
3. Sign payment with your wallet (USDC on Base)
4. Retry request with payment proof in header
5. Server verifies on-chain and returns data

## Free Endpoints (no payment needed)
- GET /v1/prices — Crypto prices
- GET /v1/fear-greed — Fear & Greed index
- GET /v1/trending — Trending tokens
- GET /v1/gas — Gas prices
- GET /v1/news — Crypto news
- GET /v1/global — Global market stats

## MCP Server
Endpoint: https://agentservices.to/mcp
Transport: Streamable HTTP
Tools: 38 (free + paid)
Auth: None for free tools. Paid tools use x402.

## Contact
Email: hustlemode@agentmail.to
Website: https://agentservices.to
""", media_type="text/plain")


# --- agents.json (structured agent discovery per agents-txt spec) ---
@app.get("/agents.json", tags=["Discovery"],
         summary="Structured agent discovery metadata",
         include_in_schema=False)
async def agents_json():
    """Structured metadata for agent discovery per the agents-txt.com specification."""
    return {
        "name": "AgentServices",
        "description": "Paid APIs for AI agents. 53 services covering crypto data, market intelligence, on-chain analytics, DeFi strategy, AI inference, web extraction, and more. All via x402 (USDC on Base).",
        "url": "https://agentservices.to",
        "version": "5.3.0",
        "contact": {
            "email": "hustlemode@agentmail.to",
        },
        "capabilities": {
            "payment": {
                "protocol": "x402",
                "version": 2,
                "network": "eip155:8453",
                "asset": "USDC",
            },
            "mcp": {
                "endpoint": "https://agentservices.to/mcp",
                "transport": "streamable-http",
                "tools": 38,
            },
            "api": {
                "openapi": "https://agentservices.to/openapi.json",
                "docs": "https://agentservices.to/docs",
                "health": "https://agentservices.to/health",
            },
        },
        "endpoints": {
            "free": [
                "GET /v1/prices — Crypto prices",
                "GET /v1/fear-greed — Market sentiment",
                "GET /v1/trending — Trending tokens",
                "GET /v1/gas — Gas prices",
                "GET /v1/global — Global market stats",
            ],
            "paid": [
                "GET /v1/indicators/{symbol} — Technical indicators ($0.02)",
                "GET /v1/yields — DeFi yields ($0.02)",
                "GET /v1/search?q=... — Web search ($0.01)",
                "GET /v1/portfolio?address=... — Portfolio intelligence ($0.10)",
                "GET /v1/market-pulse — Market pulse ($0.05)",
                "GET /v1/onchain-overview — On-chain overview ($0.15)",
                "GET /v1/defi-strategy — DeFi strategy ($0.25)",
            ],
        },
        "integrations": {
            "python_sdk": "pip install agentservices",
            "npm": "npx agentservices-mcp",
            "mcp_server": "https://agentservices.to/mcp",
        },
    }


# --- 402 Index domain verification ---
@app.get("/.well-known/402index-verify.txt", include_in_schema=False)
async def forty_two_index_verify():
    """402 Index domain verification file."""
    from starlette.responses import PlainTextResponse
    return PlainTextResponse(content="d570ef2b5d152ae5c898973566093300216490b3c0557613fbaa5073ff7c978a", media_type="text/plain")


# --- Custom OpenAPI with x-payment-info (x402 v2 discovery convention) ---
# Modern x402 indexers scan OpenAPI specs for x-payment-info per operation
# instead of relying solely on /.well-known/x402.json

_PAID_OPERATIONS = {
    "/v1/indicators/{symbol}": "$0.02",
    "/v1/yields": "$0.02",
    "/v1/metadata": "$0.01",
    "/v1/search": "$0.01",
    "/v1/marketing/sentiment": "$0.03",
    "/v1/marketing/trends": "$0.04",
    "/v1/marketing/competitors": "$0.05",
    "/v1/marketing/content-gaps": "$0.04",
    "/v1/marketing/ad-copy": "$0.05",
    "/v1/whales": "$0.02",
    "/v1/exchange-flows": "$0.02",
    "/v1/correlation": "$0.03",
    "/v1/defi-tvl": "$0.02",
    "/v1/stablecoin-flows": "$0.02",
    "/v1/github-velocity": "$0.02",
    "/v1/agent-context": "$0.02",
    "/v1/macro": "$0.03",
    "/v1/inference": "$0.03",
    "/v1/quick-complete": "$0.03",
    "/v1/token-risk": "$0.03",
    "/v1/crypto-signals": "$0.04",
    "/v1/hn-sentiment": "$0.02",
    "/v1/npm-stats": "$0.02",
    "/v1/github-trending": "$0.02",
    "/v1/yield-comparison": "$0.03",
    "/v1/stock/quote": "$0.02",
    "/v1/stock/history": "$0.02",
    "/v1/sec/filings": "$0.03",
    "/v1/commodities": "$0.02",
    "/v1/economic": "$0.02",
    "/v1/fx-rates": "$0.003",
    "/v1/gov/us/ca/entity": "$0.03",
    "/v1/extract": "$0.002",
    "/v1/security/{package}": "$0.02",
    "/v1/seo/keywords": "$0.01",
    "/v1/research": "$0.05",
    "/v1/portfolio": "$0.10",
    "/v1/defi-strategy": "$0.25",
    "/v1/market-pulse": "$0.05",
    "/v1/onchain-overview": "$0.15",
    "/v1/arbitrage": "$0.08",
    "/v1/liquidation-map": "$0.12",
    "/v1/memory/{key}": "$0.01",
    "/v1/memory/search": "$0.02",
    "/v1/skills/crypto-dossier": "$0.10",
    "/v1/skills/stock-dossier": "$0.05",
    "/v1/skills/market-overview": "$0.05",
    "/v1/disputes": "$0.05",
}


def _custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = _original_openapi()
    # Inject x-payment-info into each paid operation
    for path, path_item in schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if method in ("get", "post", "put", "delete", "patch"):
                # Check exact path or wildcard match
                price = _PAID_OPERATIONS.get(path)
                if not price:
                    # Try wildcard match (e.g., /v1/security/{package} → /v1/security/*)
                    for pattern, p in _PAID_OPERATIONS.items():
                        if pattern.replace("*", "") in path:
                            price = p
                            break
                if price:
                    operation["x-payment-info"] = {
                        "protocol": "x402",
                        "version": "2",
                        "amount": price,
                        "asset": "USDC",
                        "network": "base",
                        "chainId": "eip155:8453",
                        "payTo": os.environ.get("X402_WALLET_ADDRESS", os.environ.get("X402_PAY_TO", "0x9863aB6242663FCc84c33632741711dB78f8Fd15")),
                        "facilitator": os.environ.get("X402_FACILITATOR_URL", "https://api.cdp.coinbase.com/platform/v2/x402"),
                    }
                else:
                    operation["x-payment-info"] = {
                        "protocol": "x402",
                        "version": "2",
                        "amount": "$0.00",
                        "asset": "USDC",
                        "network": "base",
                        "free": True,
                    }
    # Inject x-bazaar-info into each operation for CDP Bazaar indexing
    for path, path_item in schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if method in ("get", "post", "put", "delete", "patch"):
                route_desc = operation.get("summary", "") or operation.get("description", "")
                bazaar_ext = _build_bazaar_extension(path, route_desc)
                if bazaar_ext.get("info"):
                    operation["x-bazaar-info"] = bazaar_ext

    app.openapi_schema = schema
    return schema


_original_openapi = app.openapi
app.openapi = _custom_openapi


# ============================================================
# MEDIA GATEWAY (v5.3.0 — Image, TTS, Multi-Model)
# ============================================================

class ImageRequest(BaseModel):
    prompt: str = Field(description="Image generation prompt")
    size: str = Field(default="1024x1024", description="Image size: 1024x1024, 1792x1024, 1024x1792")
    model: str = Field(default="gpt-image-2", description="Image model")

# (Legacy media endpoints removed — now defined above in the Inference/Media sections)


# ============================================================
# IDENTITY, REPUTATION & EVIDENCE (ERC-8004-compatible)
# ============================================================

class AgentRegistration(BaseModel):
    wallet: str = Field(min_length=3)
    name: str = Field(min_length=1)
    endpoint: str = ""
    metadata: dict = Field(default_factory=dict)

class FeedbackRequest(BaseModel):
    score: int = Field(ge=0, le=100)
    comment: str = ""
    job_id: str = ""
    evaluator: str = ""

class EvidenceRequest(BaseModel):
    agent_id: str = ""
    subject: str = Field(min_length=1)
    data: object
    source: str = ""

class ClaimsRequest(BaseModel):
    evidence_ids: list[str] = Field(min_length=1)

@app.get("/v1/erc8004/provider", tags=["Identity"])
async def erc8004_provider_info():
    return erc8004_provider.provider_info()

@app.get("/v1/erc8004/agents", tags=["Identity"])
async def erc8004_agents(limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0), chain_id: int | None = None, payment: str = ""):
    try:
        return erc8004_provider.agents(limit, offset, chain_id, payment)
    except RuntimeError as error:
        raise HTTPException(status_code=getattr(error, "status_code", 502), detail=getattr(error, "detail", str(error)))

@app.get("/v1/erc8004/agents/{agent_id}", tags=["Identity"])
async def erc8004_agent(agent_id: str, payment: str = ""):
    try:
        return erc8004_provider.agent(agent_id, payment)
    except RuntimeError as error:
        raise HTTPException(status_code=getattr(error, "status_code", 502), detail=getattr(error, "detail", str(error)))

@app.get("/v1/erc8004/agents/{agent_id}/reputation", tags=["Identity"])
async def erc8004_reputation(agent_id: str, payment: str = ""):
    try:
        return erc8004_provider.reputation(agent_id, payment)
    except RuntimeError as error:
        raise HTTPException(status_code=getattr(error, "status_code", 502), detail=getattr(error, "detail", str(error)))

@app.get("/v1/erc8004/agents/{agent_id}/feedback", tags=["Identity"])
async def erc8004_feedback(agent_id: str, limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0), payment: str = ""):
    try:
        return erc8004_provider.feedback(agent_id, limit, offset, payment)
    except RuntimeError as error:
        raise HTTPException(status_code=getattr(error, "status_code", 502), detail=getattr(error, "detail", str(error)))

@app.get("/v1/erc8004/agents/{agent_id}/validations", tags=["Identity"])
async def erc8004_validations(agent_id: str, limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0), payment: str = ""):
    try:
        return erc8004_provider.validations(agent_id, limit, offset, payment)
    except RuntimeError as error:
        raise HTTPException(status_code=getattr(error, "status_code", 502), detail=getattr(error, "detail", str(error)))

@app.post("/v1/agents/register", tags=["Identity"])
async def agent_register(req: AgentRegistration):
    return register_agent(req.wallet, req.name, req.endpoint, req.metadata)

@app.get("/v1/agents/{agent_id}", tags=["Identity"])
async def agent_detail(agent_id: str):
    agent = get_agent(agent_id)
    if not agent:
        from fastapi import HTTPException
        raise HTTPException(404, "agent not found")
    return agent

@app.post("/v1/agents/{agent_id}/feedback", tags=["Identity"])
async def agent_feedback(agent_id: str, req: FeedbackRequest):
    try:
        return add_feedback(agent_id, req.score, req.comment, req.job_id, req.evaluator)
    except KeyError:
        from fastapi import HTTPException
        raise HTTPException(404, "agent not found")

@app.get("/v1/agents/{agent_id}/reputation", tags=["Identity"])
async def agent_reputation(agent_id: str):
    try:
        return reputation(agent_id)
    except KeyError:
        from fastapi import HTTPException
        raise HTTPException(404, "agent not found")

@app.post("/v1/agents/{agent_id}/verify", tags=["Identity"])
async def agent_verify(agent_id: str, challenge: str = ""):
    try:
        return verify_agent(agent_id, challenge)
    except KeyError:
        from fastapi import HTTPException
        raise HTTPException(404, "agent not found")

@app.post("/v1/evidence/snapshot", tags=["Evidence"])
async def evidence_snapshot(req: EvidenceRequest):
    return snapshot(req.agent_id, req.subject, req.data, req.source)

@app.post("/v1/evidence/verify", tags=["Evidence"])
async def evidence_verify(evidence_id: str):
    try:
        return verify_evidence(evidence_id)
    except KeyError:
        from fastapi import HTTPException
        raise HTTPException(404, "evidence not found")

@app.post("/v1/claims/check", tags=["Evidence"])
async def claims_check(req: ClaimsRequest):
    return check_claims(req.evidence_ids)

# ============================================================
# VOICE GATEWAY (v5.3.0 — Phone, Calls)
# ============================================================

@app.get("/v1/phone", tags=["Voice"],
          summary="Phone Number Info",
          description="Get the AgentServices phone number and capabilities. FREE.")
async def phone_info():
    """Phone number info (FREE)"""
    return get_phone_number()


# ============================================================
# VOICE GATEWAY (v5.3.0 — Phone, Calls)
# ============================================================

@app.get("/v1/phone", tags=["Voice"],
          summary="Phone Number Info",
          description="Get the AgentServices phone number and capabilities. FREE.")
async def phone_info():
    """Phone number info (FREE)"""
    return get_phone_number()

class CallRequest(BaseModel):
    to: str = Field(description="Phone number to call (E.164 format, e.g., +1234567890)")
    message: str = Field(default="", description="Message to speak on the call (text-to-speech)")

@app.post("/v1/calls", tags=["Voice"],
          summary="AI Voice Call",
          description="Make an outbound AI voice call with text-to-speech. $0.54 via x402.")
async def voice_call(req: CallRequest):
    """Voice call ($0.54 via x402)"""
    return make_call(req.to, req.message)

@app.get("/v1/lookup/{phone_number}", tags=["Voice"],
          summary="Phone Number Lookup",
          description="Look up carrier, type, and caller name for a phone number. $0.05 via x402.")
async def phone_lookup(phone_number: str):
    """Phone lookup ($0.05 via x402)"""
    return lookup_number(phone_number)
