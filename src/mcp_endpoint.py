"""
Remote MCP transport endpoint for AgentServices.
Allows AI tools (Claude, Cursor, etc.) to connect directly without installing anything.
Implements MCP 2026-07-28 spec (stateless, header-driven routing) with backward compat.
"""
import json
import asyncio
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse

router = APIRouter()

# Protocol versions supported (2026-07-28 is the new stateless spec; 2024-11-05 is legacy)
MCP_PROTOCOL_VERSION = "2026-07-28"
MCP_LEGACY_VERSION = "2024-11-05"

# MCP tool definitions matching our API endpoints
MCP_TOOLS = [
    {
        "name": "crypto_prices",
        "description": "Get current crypto prices for one or more symbols (FREE)",
        "title": "Get Crypto Prices",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "string",
                    "description": "Comma-separated crypto symbols (e.g. BTC,ETH,SOL)",
                    "default": "BTC,ETH,SOL,XRP"
                }
            }
        }
    },
    {
        "name": "technical_indicators",
        "description": "Get technical indicators (RSI, MACD, Bollinger Bands) for a crypto symbol ($0.02 x402)",
        "title": "Technical Indicators Analysis",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Crypto symbol (e.g. BTC)"}
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "defi_yields",
        "description": "Get top DeFi yield pools ranked by TVL ($0.02 x402)",
        "title": "DeFi Yield Pools",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max results", "default": 20}
            }
        }
    },
    {
        "name": "fear_greed",
        "description": "Get crypto Fear & Greed sentiment index (FREE)",
        "title": "Fear & Greed Index",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "ip_geolocation",
        "description": "Get geolocation data for an IP address (FREE)",
        "title": "IP Geolocation Lookup",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "ip": {"type": "string", "description": "IP address (e.g. 1.2.3.4)"}
            },
            "required": ["ip"]
        }
    },
    {
        "name": "url_metadata",
        "description": "Extract metadata from a URL — title, description, images ($0.01 x402)",
        "title": "URL Metadata Extractor",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to extract metadata from"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "web_search",
        "description": "Web search with structured results — same as GET /v1/search ($0.01 x402)",
        "title": "Web Search",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "q": {"type": "string", "description": "Search query"},
                "num_results": {"type": "integer", "description": "Max results", "default": 5}
            },
            "required": ["q"]
        }
    },
    {
        "name": "resolve_dispute",
        "description": "Submit a dispute for AI-powered policy-driven ruling. 7 policy templates available ($0.05 x402)",
        "title": "AI Dispute Resolution",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "policy": {
                    "type": "string",
                    "description": "Policy template: freelance-delivery, milestone-payment, sla-monitoring, api-quality, bug-bounty, scope-dispute, physical-commerce",
                    "enum": [
                        "freelance-delivery", "milestone-payment", "sla-monitoring",
                        "api-quality", "bug-bounty", "scope-dispute", "physical-commerce"
                    ]
                },
                "claimant": {"type": "string", "description": "Plaintiff address or agent ID"},
                "respondent": {"type": "string", "description": "Respondent address or agent ID"},
                "claim": {"type": "string", "description": "What happened"},
                "desired_remedy": {"type": "string", "description": "What the claimant wants"},
                "evidence": {"type": "array", "items": {"type": "string"}, "description": "Evidence items"}
            },
            "required": ["policy", "claimant", "respondent"]
        }
    },
    {
        "name": "list_policies",
        "description": "List all available dispute resolution policy templates (FREE)",
        "title": "List Dispute Policies",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "marketing_sentiment",
        "description": "AI-powered brand sentiment analysis across platforms (FREE beta)",
        "title": "Brand Sentiment Analysis",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "brand": {"type": "string", "description": "Brand name to analyze"},
                "platforms": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Platforms to check",
                    "default": ["twitter", "reddit", "tiktok"]
                }
            },
            "required": ["brand"]
        }
    },
    {
        "name": "marketing_trends",
        "description": "Detect trending marketing topics in any industry (FREE beta)",
        "title": "Marketing Trends Detection",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "industry": {"type": "string", "description": "Industry (e.g. fintech, ecommerce)"},
                "limit": {"type": "integer", "description": "Max results", "default": 5}
            },
            "required": ["industry"]
        }
    },
    {
        "name": "marketing_ad_copy",
        "description": "Generate ad copy for Google, Meta, TikTok, or Taboola (FREE beta)",
        "title": "Ad Copy Generator",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "product": {"type": "string", "description": "Product/service name"},
                "platform": {"type": "string", "description": "Ad platform", "default": "google"},
                "tone": {"type": "string", "description": "Tone", "default": "professional"},
                "count": {"type": "integer", "description": "Number of variations", "default": 3}
            },
            "required": ["product"]
        }
    },
    {
        "name": "whale_tracking",
        "description": "Large whale transactions on BTC (>=10 BTC) and ETH chains ($0.02 x402)",
        "title": "Whale Transaction Tracker",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "exchange_flows",
        "description": "CEX reserve flows and 24h changes from DeFi Llama ($0.02 x402)",
        "title": "Exchange Flow Monitor",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "correlation_matrix",
        "description": "30-day Pearson correlation matrix across top crypto assets ($0.03 x402)",
        "title": "Asset Correlation Matrix",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "defi_tvl",
        "description": "Top DeFi protocols ranked by TVL from DeFi Llama ($0.02 x402)",
        "title": "DeFi Protocol TVL",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max results", "default": 20},
                "chain": {"type": "string", "description": "Filter by chain", "default": "all"}
            }
        }
    },
    {
        "name": "stablecoin_flows",
        "description": "Stablecoin market caps and supply data ($0.02 x402)",
        "title": "Stablecoin Supply Monitor",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "github_velocity",
        "description": "Trending crypto/web3 GitHub repos with velocity scores ($0.02 x402)",
        "title": "GitHub Velocity Tracker",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "language": {"type": "string", "description": "Filter by language", "default": ""},
                "limit": {"type": "integer", "description": "Max results", "default": 15}
            }
        }
    },
    {
        "name": "agent_context",
        "description": "Paste-ready multi-source market context for LLM system prompts (FREE)",
        "title": "Agent Market Context",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "macro_indicators",
        "description": "Macro economic indicators: global market cap, dominance, derivatives ($0.02 x402)",
        "title": "Macro Economic Indicators",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {"type": "object", "properties": {}}
    },
    # v5.0.0 — Inference Gateway
    {
        "name": "llm_inference",
        "description": "LLM inference gateway — chat completions via gpt-5.4/5.4-mini/5.5 ($0.03 x402)",
        "title": "LLM Inference Gateway",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "gpt-5.4, gpt-5.4-mini, or gpt-5.5", "default": "gpt-5.4-mini"},
                "messages": {"type": "array", "description": "Chat messages [{role, content}]"},
                "max_tokens": {"type": "integer", "default": 1000}
            },
            "required": ["messages"]
        }
    },
    # v5.0.0 — Synthesis
    {
        "name": "token_risk",
        "description": "Token risk scoring — volatility, liquidity, market cap analysis ($0.03 x402)",
        "title": "Token Risk Assessment",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {"token": {"type": "string", "description": "CoinGecko token ID (e.g. bitcoin)"}},
            "required": ["token"]
        }
    },
    {
        "name": "crypto_signals",
        "description": "Crypto buy/sell signals from RSI, moving averages, Bollinger Bands ($0.04 x402)",
        "title": "Crypto Trading Signals",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {"symbol": {"type": "string", "description": "Symbol (BTC, ETH, etc.)"}},
            "required": ["symbol"]
        }
    },
    # v5.1.0 — Traditional Finance
    {
        "name": "stock_quote",
        "description": "Real-time stock market quote from Yahoo Finance ($0.02 x402)",
        "title": "Stock Quote Lookup",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {"ticker": {"type": "string", "description": "Stock ticker (e.g. AAPL, TSLA)"}},
            "required": ["ticker"]
        }
    },
    {
        "name": "stock_history",
        "description": "Historical OHLCV stock data ($0.03 x402)",
        "title": "Stock Price History",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "range": {"type": "string", "default": "3mo", "description": "1d, 5d, 1mo, 3mo, 6mo, 1y, 5y"}
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "sec_filings",
        "description": "SEC filings parser — 10-K, 10-Q, 8-K from EDGAR ($0.03 x402)",
        "title": "SEC Filings Parser",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "filing_type": {"type": "string", "default": "10-K"}
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "commodities",
        "description": "Commodity prices — oil, gold, silver, copper, wheat ($0.03 x402)",
        "title": "Commodity Prices",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "fx_rates",
        "description": "Real-time FX/forex rates for 30+ currencies ($0.003 x402)",
        "title": "FX Exchange Rates",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {"base": {"type": "string", "default": "USD"}}
        }
    },
    # v5.1.0 — Utility
    {
        "name": "web_extract",
        "description": "Extract clean text from any URL — strips ads, nav, scripts ($0.002 x402)",
        "title": "Web Content Extractor",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "URL to extract content from"}},
            "required": ["url"]
        }
    },
    {
        "name": "package_security",
        "description": "Check PyPI/npm package for known vulnerabilities ($0.02 x402)",
        "title": "Package Security Scanner",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "package": {"type": "string", "description": "Package name"},
                "ecosystem": {"type": "string", "default": "PyPI", "description": "PyPI or npm"}
            },
            "required": ["package"]
        }
    },
    {
        "name": "seo_keywords",
        "description": "SEO keyword research with volume estimates and competition ($0.01 x402)",
        "title": "SEO Keyword Research",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {"keyword": {"type": "string"}},
            "required": ["keyword"]
        }
    },
    {
        "name": "deep_research",
        "description": "Deep research — search web + extract content + synthesize intelligence brief ($0.05 x402)",
        "title": "Deep Research Intelligence",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "q": {"type": "string", "description": "Research query"},
                "sources": {"type": "integer", "default": 3, "description": "Number of sources to analyze (max 5)"}
            },
            "required": ["q"]
        }
    },
    {
        "name": "portfolio_intelligence",
        "description": "Portfolio intelligence — price + technical signal + risk score + market sentiment in one call ($0.10 x402)",
        "title": "Portfolio Intelligence Report",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Crypto symbol (BTC, ETH, SOL, etc.)"}
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "defi_strategy",
        "description": "DeFi strategy report — top yields + protocol TVL + cross-chain comparison + risk assessment with high-APY flags ($0.25 x402)",
        "title": "DeFi Strategy Report",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "chain": {"type": "string", "description": "Filter by chain (ethereum, arbitrum, base, solana). Empty = all chains."}
            },
            "required": []
        }
    },
    {
        "name": "market_pulse",
        "description": "Market pulse — Fear & Greed + trending tokens + news + social + whale movements + global market in one snapshot ($0.05 x402)",
        "title": "Market Pulse Snapshot",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "onchain_overview",
        "description": "On-chain intelligence — whale movements + exchange flows + stablecoin flows + correlation matrix + DeFi TVL in one report ($0.15 x402)",
        "title": "On-Chain Intelligence Report",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "arbitrage_scanner",
        "description": "Cross-DEX arbitrage scanner — compares token prices across exchanges, models gas-adjusted profitability at different trade sizes, estimates slippage, flags actionable opportunities ($0.08 x402)",
        "title": "Cross-DEX Arbitrage Scanner",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "string",
                    "description": "Comma-separated token symbols to scan (e.g. 'BTC,ETH,SOL,USDC'). Default: 'BTC,ETH,SOL,USDC,WETH,WBTC'"
                }
            },
            "required": []
        }
    },
    {
        "name": "liquidation_map",
        "description": "DeFi liquidation heatmap — calculates liquidation prices across Aave V3, Compound V3, and MakerDAO for any token. Models cascading liquidation risk, estimates volume at risk, flags critical price zones ($0.12 x402)",
        "title": "DeFi Liquidation Map",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "string",
                    "description": "Comma-separated token symbols to analyze (e.g. 'BTC,ETH,LINK'). Default: 'BTC,ETH,LINK,AAVE,UNI'"
                }
            },
            "required": []
        }
    },
    {
        "name": "chat",
        "description": "LLM chat completion — 400+ models (GPT, Claude, Gemini, DeepSeek, Grok, Llama). Use model='auto' for smart routing. OpenAI-compatible ($0.03 x402)",
        "title": "AI Chat Completion",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model ID or 'auto' for smart routing", "default": "auto"},
                "messages": {"type": "array", "items": {"type": "object"}, "description": "Chat messages [{role, content}]"},
                "temperature": {"type": "number", "default": 0.7},
                "max_tokens": {"type": "integer", "default": 1000},
                "profile": {"type": "string", "description": "Router profile: auto/eco/premium/free", "default": "auto"}
            },
            "required": ["messages"]
        }
    },
    {
        "name": "generate_image",
        "description": "Generate an AI image from a text prompt via gpt-image-2 ($0.05 x402)",
        "title": "AI Image Generation",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Image description"},
                "size": {"type": "string", "default": "1024x1024", "description": "256x256, 512x512, or 1024x1024"}
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "text_to_speech",
        "description": "Convert text to speech audio with natural voices ($0.05 x402)",
        "title": "Text-to-Speech",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to convert to speech"},
                "voice": {"type": "string", "default": "alloy", "description": "Voice: alloy, echo, fable, onyx, nova, shimmer"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "buy_credits",
        "description": "Get a Stripe Checkout URL to buy a $10 prepaid credit pack (requires Google OAuth login)",
        "title": "Buy Credits",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "credit_balance",
        "description": "Check your prepaid credit balance (requires Google OAuth login)",
        "title": "Credit Balance",
        "annotations": {"readOnlyHint": True},
        "inputSchema": {"type": "object", "properties": {}}
    },
]

MCP_RESOURCES = [
    {
        "uri": "agentservices://prices",
        "name": "Live Crypto Prices",
        "description": "Current crypto prices (BTC, ETH, SOL, XRP)",
        "mimeType": "application/json"
    },
    {
        "uri": "agentservices://policies",
        "name": "Dispute Policy Templates",
        "description": "Available dispute resolution policies",
        "mimeType": "application/json"
    }
]

from discovery_surfaces import MCP_URL, mcp_auth_metadata, mcp_pricing_metadata


def build_server_card() -> dict:
    """MCP server card for GEO/discovery crawlers (Smithery, ChatGPT, mcp-marketplace.io)."""
    description = (
        "Paid APIs for AI agents — 53 services, 41 paid. 37 MCP tools. "
        "ChatGPT connector: Google OAuth + Stripe credits at "
        f"{MCP_URL}. Wallet agents: x402 USDC on Base for REST."
    )
    card = {
        "serverInfo": {
            "name": "AgentServices",
            "version": "5.3.0",
            "description": description,
        },
        "transport": {
            "type": "streamable-http",
            "endpoint": MCP_URL,
        },
        "authentication": mcp_auth_metadata(),
        "pricing": {
            "model": "pay-per-use",
            "protocol": "x402 (HTTP 402)",
            "currency": "USDC on Base",
            "rest": "Wallet agents pay via HTTP 402 on REST endpoints",
            "free_tools": ["crypto_prices", "fear_greed", "ip_geolocation", "list_policies", "agent_context"],
            "paid_tools": {
                "technical_indicators": "$0.02",
                "defi_yields": "$0.02",
                "url_metadata": "$0.01",
                "resolve_dispute": "$0.05",
                "whale_tracking": "$0.02",
                "exchange_flows": "$0.02",
                "correlation_matrix": "$0.03",
                "defi_tvl": "$0.02",
                "stablecoin_flows": "$0.02",
                "github_velocity": "$0.02",
                "macro_indicators": "$0.02",
            },
        },
        "repository": "https://github.com/vbkotecha/agentservices-api",
        "documentation": "https://agentservices.to/docs",
        "tools": [{"name": t["name"], "description": t["description"]} for t in MCP_TOOLS],
    }
    human_pricing = mcp_pricing_metadata().get("mcp_human")
    if human_pricing:
        card["pricing"]["mcp_human"] = human_pricing
    return card


def _mcp_auth_metadata() -> dict:
    return mcp_auth_metadata()


def _mcp_pricing_metadata() -> dict:
    return mcp_pricing_metadata()


@router.options("/mcp")
async def mcp_options():
    """CORS preflight handler for browser-based MCP clients."""
    return JSONResponse(
        {"status": "ok"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Mcp-Method, Mcp-Name, Authorization",
            "Access-Control-Max-Age": "86400",
        }
    )

@router.post("/mcp")
async def mcp_handler(request: Request):
    """
    MCP Streamable HTTP endpoint (2026-07-28 spec compliant).
    Stateless, header-driven routing with backward compat for legacy clients.

    New headers (2026-07-28 spec):
      Mcp-Method: The JSON-RPC method (e.g. "tools/list")
      Mcp-Name: The server name for routing

    Falls back to body.method for legacy clients.
    Includes CORS headers for browser-based MCP clients (Claude.ai, Cursor web).
    """
    # CORS preflight
    origin = request.headers.get("origin", "")
    cors_headers = {
        "Access-Control-Allow-Origin": origin or "*",
        "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Mcp-Method, Mcp-Name, Authorization",
        "Access-Control-Max-Age": "86400",
    }

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}},
            status_code=400
        )

    # Extract method: prefer 2026-07-28 headers, fall back to body (legacy compat)
    header_method = request.headers.get("mcp-method", "")
    body_method = body.get("method", "")
    method = header_method or body_method

    # Header-vs-body consistency (tolerate mismatch during transition)
    # In production post-July-28: reject if header and body methods disagree

    req_id = body.get("id")
    params = body.get("params", {})

    # --- server/discover (2026-07-28 spec — replaces initialize) ---
    if method == "server/discover":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"listChanged": False},
                },
                "serverInfo": {
                    "name": "AgentServices",
                    "version": "5.3.0",
                    "description": "Paid APIs for AI agents — 53 services, 41 paid. x402 on Base.",
                },
                "instructions": "Use tools/list to see available tools. Free tools: crypto_prices, fear_greed, ip_geolocation, list_policies, agent_context. Paid tools return HTTP 402 for x402 payment.",
            }
        }

    # --- initialize (legacy compat — deprecated, will be removed post July 28) ---
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"listChanged": False},
                },
                "serverInfo": {
                    "name": "AgentServices",
                    "version": "5.3.0",
                }
            }
        }

    # --- tools/list (with cache metadata per 2026-07-28 spec) ---
    if method == "tools/list":
        response = JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": MCP_TOOLS,
                    # 2026-07-28 cache hints — clients may cache tool list for 5 min
                    "_meta": {
                        "ttlMs": 300000,  # 5 minutes
                        "cacheScope": "global",
                    }
                }
            },
            headers={
                "Cache-Control": "public, max-age=300",
                "Access-Control-Allow-Origin": "*",
            }
        )
        return response

    # --- resources/list ---
    if method == "resources/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"resources": MCP_RESOURCES}
        }

    # --- tools/call ---
    if method == "tools/call":
        tool_name = params.get("name", "")
        args = params.get("arguments", {})

        billing_ctx, billing_error = _prepare_billing(request, tool_name, req_id)
        if billing_error:
            return JSONResponse(billing_error, status_code=402)

        result = await _execute_tool(tool_name, args, request)

        if billing_ctx:
            _finalize_billing(billing_ctx, result)

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
                    }
                ]
            }
        }

    # --- notifications/initialized (legacy compat — no-op in 2026-07-28) ---
    if method == "notifications/initialized":
        return Response(status_code=204)

    # --- ping ---
    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    # Unknown method
    return JSONResponse(
        {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}},
        status_code=400
    )


def _is_tool_failure(result) -> bool:
    return isinstance(result, dict) and bool(result.get("error"))


def _prepare_billing(request: Request, tool_name: str, req_id):
    """Check auth and balance for paid MCP tools. Debit happens after success."""
    from human_billing.pricing import is_paid_mcp_tool, tool_price_usd
    from human_billing.router import authenticate_mcp_request
    from human_billing.config import credits_enabled, oauth_enabled
    from human_billing.credits import get_balance, InsufficientCredits
    from human_billing.stripe_billing import create_checkout_session

    if not is_paid_mcp_tool(tool_name):
        return None, None

    user = authenticate_mcp_request(request)
    if not user:
        if oauth_enabled():
            return None, {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32000,
                    "message": "Authentication required for paid MCP tools. Connect via Google OAuth in ChatGPT.",
                },
            }
        return None, None

    if not credits_enabled():
        return None, {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32002,
                "message": "Credits billing is not configured on this deployment.",
            },
        }

    price = tool_price_usd(tool_name)
    balance = get_balance(user["sub"])
    if balance < price:
        exc = InsufficientCredits(balance, price)
        checkout = create_checkout_session(
            google_sub=user["sub"],
            email=user.get("email", ""),
        )
        return None, {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32001,
                "message": (
                    f"Insufficient credits: balance ${exc.balance}, need ${exc.required}. "
                    "Buy a $10 credit pack to continue."
                ),
                "data": {
                    "balance_usd": str(exc.balance.normalize()),
                    "required_usd": str(exc.required.normalize()),
                    "checkout_url": checkout["checkout_url"],
                },
            },
        }

    return {"user": user, "price": price, "tool": tool_name}, None


def _finalize_billing(billing_ctx: dict, result) -> None:
    """Debit credits only after a successful tool execution."""
    from human_billing.credits import debit_balance

    if _is_tool_failure(result):
        return
    debit_balance(
        billing_ctx["user"]["sub"],
        billing_ctx["price"],
        tool=billing_ctx["tool"],
    )


async def _execute_tool(tool_name: str, args: dict, request: Request | None = None):
    """Execute a tool call and return the result."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    try:
        if tool_name == "buy_credits":
            from human_billing.router import authenticate_mcp_request
            from human_billing.config import credits_enabled
            from human_billing.stripe_billing import create_checkout_session
            if not credits_enabled():
                return {"error": "Credits billing is not configured"}
            user = authenticate_mcp_request(request) if request else None
            if not user:
                return {"error": "Sign in with Google OAuth first (Connect in ChatGPT)"}
            session = create_checkout_session(google_sub=user["sub"], email=user.get("email", ""))
            return {
                "checkout_url": session["checkout_url"],
                "pack_usd": 10,
                "message": "Open this URL to buy $10 in prepaid credits.",
            }

        if tool_name == "credit_balance":
            from human_billing.router import authenticate_mcp_request
            from human_billing.config import credits_enabled
            from human_billing.credits import get_balance
            if not credits_enabled():
                return {"error": "Credits billing is not configured"}
            user = authenticate_mcp_request(request) if request else None
            if not user:
                return {"error": "Sign in with Google OAuth first (Connect in ChatGPT)"}
            balance = get_balance(user["sub"])
            return {"balance_usd": str(balance), "email": user.get("email")}

        if tool_name == "crypto_prices":
            from crypto_data import get_multi_price
            symbols = args.get("symbols", "BTC,ETH,SOL,XRP")
            return get_multi_price(symbols.split(","))

        elif tool_name == "technical_indicators":
            from crypto_data import get_indicators
            symbol = args.get("symbol", "BTC")
            # Note: This is a paid endpoint — MCP caller needs x402 payment
            return get_indicators(symbol)

        elif tool_name == "defi_yields":
            from crypto_data import get_defi_yields
            return get_defi_yields()

        elif tool_name == "fear_greed":
            from crypto_data import get_fear_greed
            return get_fear_greed()

        elif tool_name == "ip_geolocation":
            from geo_data import get_ip_geo
            ip = args.get("ip", "")
            return get_ip_geo(ip)

        elif tool_name == "url_metadata":
            from web_data import get_url_metadata
            url = args.get("url", "")
            return get_url_metadata(url)

        elif tool_name == "web_search":
            from search_data import web_search
            q = args.get("q", "")
            if not q:
                return {"error": "Missing required argument: q"}
            return web_search(q, num_results=min(int(args.get("num_results", 5)), 10))

        elif tool_name == "resolve_dispute":
            from engine.policy_engine import evaluate_dispute
            ruling = evaluate_dispute(
                dispute={
                    "claimant": args.get("claimant", ""),
                    "respondent": args.get("respondent", ""),
                    "claim": args.get("claim", ""),
                    "desired_remedy": args.get("desired_remedy", ""),
                },
                evidence=args.get("evidence", []),
                policy_name=args.get("policy", "freelance-delivery"),
            )
            return ruling

        elif tool_name == "list_policies":
            from engine.policy_engine import list_policies
            return list_policies()

        elif tool_name == "whale_tracking":
            from onchain_data import get_whales
            return get_whales()

        elif tool_name == "exchange_flows":
            from onchain_data import get_exchange_flows
            return get_exchange_flows()

        elif tool_name == "correlation_matrix":
            from onchain_data import get_correlation_matrix
            return get_correlation_matrix()

        elif tool_name == "defi_tvl":
            from onchain_data import get_defi_tvl
            return get_defi_tvl(args.get("limit", 20), args.get("chain", "all"))

        elif tool_name == "stablecoin_flows":
            from onchain_data import get_stablecoin_flows
            return get_stablecoin_flows()

        elif tool_name == "github_velocity":
            from onchain_data import get_github_velocity
            return get_github_velocity(args.get("language", ""), args.get("limit", 15))

        elif tool_name == "agent_context":
            from onchain_data import get_agent_context
            return get_agent_context()

        elif tool_name == "macro_indicators":
            from onchain_data import get_macro
            return get_macro()

        # v5.0+ tools
        elif tool_name == "llm_inference":
            from inference_gateway import inference
            return inference(model=args.get("model", "gpt-5.4-mini"), messages=args.get("messages", []), max_tokens=args.get("max_tokens", 1000))
        elif tool_name == "token_risk":
            from synthesis_data import get_token_risk
            return get_token_risk(args.get("token", "bitcoin"))
        elif tool_name == "crypto_signals":
            from synthesis_data import get_crypto_signal
            return get_crypto_signal(args.get("symbol", "BTC"))
        elif tool_name == "stock_quote":
            from tradfi_data import get_stock_quote
            return get_stock_quote(args.get("ticker", "AAPL"))
        elif tool_name == "stock_history":
            from tradfi_data import get_stock_history
            return get_stock_history(args.get("ticker", "AAPL"), args.get("range", "3mo"))
        elif tool_name == "sec_filings":
            from tradfi_data import get_sec_filings
            return get_sec_filings(args.get("ticker", "AAPL"), args.get("filing_type", "10-K"))
        elif tool_name == "commodities":
            from tradfi_data import get_commodities
            return get_commodities()
        elif tool_name == "fx_rates":
            from tradfi_data import get_fx_rates
            return get_fx_rates(args.get("base", "USD"))
        elif tool_name == "web_extract":
            from utility_data import extract_web_content
            return extract_web_content(args.get("url", ""))
        elif tool_name == "package_security":
            from utility_data import scan_package_security
            return scan_package_security(args.get("package", "requests"), args.get("ecosystem", "PyPI"))
        elif tool_name == "seo_keywords":
            from utility_data import seo_keywords
            return seo_keywords(args.get("keyword", ""))
        elif tool_name == "deep_research":
            from synthesis_data import deep_research
            return deep_research(args.get("q", ""), max_sources=min(args.get("sources", 3), 5))
        elif tool_name == "portfolio_intelligence":
            from synthesis_data import portfolio_intelligence
            return portfolio_intelligence(args.get("symbol", "BTC"))
        elif tool_name == "defi_strategy":
            from synthesis_data import defi_strategy_report
            return defi_strategy_report(args.get("chain", ""))
        elif tool_name == "market_pulse":
            from synthesis_data import market_pulse
            return market_pulse()
        elif tool_name == "onchain_overview":
            from synthesis_data import onchain_overview
            return onchain_overview()
        elif tool_name == "arbitrage_scanner":
            from synthesis_data import arbitrage_scanner
            return arbitrage_scanner(args.get("symbols", "BTC,ETH,SOL,USDC,WETH,WBTC"))
        elif tool_name == "liquidation_map":
            from synthesis_data import liquidation_map
            return liquidation_map(args.get("symbols", "BTC,ETH,LINK,AAVE,UNI"))
        elif tool_name == "chat":
            from inference_gateway import inference
            return inference(
                model=args.get("model", "auto"),
                messages=args.get("messages", []),
                temperature=args.get("temperature", 0.7),
                max_tokens=args.get("max_tokens", 1000),
                profile=args.get("profile", "auto"),
            )
        elif tool_name == "generate_image":
            from media_gateway import generate_image
            return generate_image(prompt=args.get("prompt", ""), size=args.get("size", "1024x1024"))
        elif tool_name == "text_to_speech":
            from media_gateway import text_to_speech
            return text_to_speech(text=args.get("text", ""), voice=args.get("voice", "alloy"))

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        return {"error": str(e)}


@router.get("/mcp/tools")
async def mcp_tools_summary():
    """Human-readable summary of MCP tools for discovery."""
    return build_server_card()

@router.get("/.well-known/mcp/server-card.json")
async def mcp_server_card():
    """MCP server card for registry discovery (Smithery, ChatGPT, mcp-marketplace.io)."""
    return build_server_card()

@router.get("/.well-known/mcp")
async def mcp_well_known():
    """SEP-1960 MCP discovery manifest — terse, machine-first.
    Enumerates transport endpoints and capabilities for auto-discovery.
    Probed by Claude Desktop and other MCP clients.
    """
    return JSONResponse(
        {
            "version": MCP_PROTOCOL_VERSION,
            "legacyVersions": [MCP_LEGACY_VERSION],
            "name": "AgentServices",
            "description": "Paid APIs for AI agents — crypto market data, DeFi yields, on-chain analytics, dispute resolution. x402 payments on Base.",
            "transports": {
                "streamable-http": {
                    "endpoint": "https://agentservices.to/mcp",
                    "capabilities": {"tools": True, "resources": False, "prompts": False}
                }
            },
            "authentication": _mcp_auth_metadata(),
            "pricing": _mcp_pricing_metadata(),
            "repository": "https://github.com/vbkotecha/agentservices-api",
            "tools_count": len(MCP_TOOLS),
            "links": {
                "server-card": "https://agentservices.to/.well-known/mcp/server-card.json",
                "documentation": "https://agentservices.to/docs",
                "health": "https://agentservices.to/health"
            }
        },
        headers={"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
    )
