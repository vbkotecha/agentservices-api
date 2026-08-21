"""
LangChain Tool Wrappers for AgentServices
==========================================
50 endpoints for LangChain agents. Modern @tool + StructuredTool patterns.

Usage:
    from agentservices import create_langchain_tools
    tools = create_langchain_tools()
    agent = create_react_agent(llm, tools)

    # Or with wallet for auto-pay:
    tools = create_langchain_tools(wallet_private_key="0x...")
"""
import json
from typing import Optional, List
from .client import AgentServicesClient

_client = None

def _get_client(wallet_private_key: Optional[str] = None, base_url: Optional[str] = None):
    global _client
    if _client is None or wallet_private_key or base_url:
        _client = AgentServicesClient(
            wallet_private_key=wallet_private_key,
            base_url=base_url or "https://agentservices.to"
        )
    return _client

def _safe_json(response) -> str:
    """Convert response to JSON string, handle x402 payment responses."""
    if isinstance(response, dict) and response.get("x402_requires_payment"):
        accepts = response.get("accepts", [])
        if accepts:
            req = accepts[0]
            return (f"⚠️ Payment required: {req.get('maxAmountRequired', '?')} USDC "
                    f"on {req.get('network', 'base')}. "
                    f"Configure wallet to auto-pay: AgentServicesClient(wallet_private_key='0x...')")
    return json.dumps(response, indent=2, default=str)

def _call(method_name: str, **kwargs) -> str:
    """Generic wrapper for client methods."""
    client = _get_client()
    try:
        method = getattr(client, method_name)
        result = method(**kwargs)
        return _safe_json(result)
    except Exception as e:
        return f"Error calling {method_name}: {str(e)}"

def create_langchain_tools(
    wallet_private_key: Optional[str] = None,
    base_url: Optional[str] = None,
    endpoints: Optional[List[str]] = None,
) -> list:
    """
    Create LangChain Tool objects for AgentServices endpoints.

    Args:
        wallet_private_key: EVM private key for x402 auto-pay (optional)
        base_url: Override API base URL
        endpoints: List of endpoint names to include (default: all)

    Returns:
        List of LangChain Tool objects
    """
    _get_client(wallet_private_key, base_url)

    try:
        from langchain.tools import Tool
    except ImportError:
        raise ImportError("langchain is required: pip install langchain")

    all_tools = [
        Tool(
            name="crypto_prices",
            func=lambda symbols="BTC,ETH": _call("get_prices", symbols=symbols),
            description="Get current crypto prices. Input: comma-separated symbols like 'BTC,ETH,XRP'. FREE. Example: crypto_prices('BTC,ETH')",
        ),
        Tool(
            name="technical_indicators",
            func=lambda symbol="BTC", interval="1d": _call("get_indicators", symbol=symbol, interval=interval),
            description="Get technical indicators (RSI, MACD, Bollinger Bands) for a crypto symbol. Input: symbol, interval. $0.02 per call. Example: technical_indicators('BTC')",
        ),
        Tool(
            name="defi_yields",
            func=lambda chain="": _call("get_defi_yields", chain=chain or None),
            description="Get DeFi yield rates across protocols (Aave, Compound, etc.). Input: chain name (ethereum, arbitrum, base) or empty for all. $0.02. Example: defi_yields('ethereum')",
        ),
        Tool(
            name="fear_greed_index",
            func=lambda: _call("get_fear_greed"),
            description="Get crypto Fear & Greed sentiment index (0=extreme fear, 100=extreme greed). No input. FREE.",
        ),
        Tool(
            name="ip_geolocation",
            func=lambda ip="": _call("get_geo", ip=ip or None),
            description="Get geolocation for an IP address. Input: IP or empty for your own. FREE.",
        ),
        Tool(
            name="url_metadata",
            func=lambda url="": _call("get_url_metadata", url=url),
            description="Extract metadata (title, description, OG tags) from a URL. Input: full URL. $0.01.",
        ),
        Tool(
            name="crypto_search",
            func=lambda query="": _call("search", query=query),
            description="Search the web for crypto/blockchain information. Input: search query. $0.01. Example: crypto_search('Bitcoin ETF inflows')",
        ),
        Tool(
            name="swap_quote",
            func=lambda token_in="USDC", token_out="BTC", amount="100", chain="base": _call("get_swap_quote", token_in=token_in, token_out=token_out, amount=amount, chain=chain),
            description="Get a DEX swap quote. Input: token_in, token_out, amount, chain. FREE. Example: swap_quote('USDC', 'ETH', '1000', 'base')",
        ),
        Tool(
            name="trending_tokens",
            func=lambda: _call("get_trending"),
            description="Get trending crypto tokens. No input. FREE.",
        ),
        Tool(
            name="gas_tracker",
            func=lambda chain="": _call("get_gas", chain=chain or None),
            description="Get current gas prices across chains. Input: chain or empty for all. FREE.",
        ),
        Tool(
            name="market_predictions",
            func=lambda: _call("get_predictions"),
            description="Get market predictions and analysis from multiple sources. No input. FREE.",
        ),
        Tool(
            name="crypto_news",
            func=lambda: _call("get_news"),
            description="Get latest crypto news headlines. No input. FREE.",
        ),
        Tool(
            name="social_trending",
            func=lambda: _call("get_social_trending"),
            description="Get trending topics on crypto social media. No input. FREE.",
        ),
        Tool(
            name="global_market",
            func=lambda: _call("get_global"),
            description="Get global crypto market cap, volume, BTC dominance. No input. FREE.",
        ),
        Tool(
            name="marketing_sentiment",
            func=lambda brand="": _call("get_marketing_sentiment", brand=brand),
            description="Analyze brand sentiment across social media. Input: brand name. $0.03. Example: marketing_sentiment('Coinbase')",
        ),
        Tool(
            name="marketing_competitors",
            func=lambda brand="": _call("get_marketing_competitors", brand=brand),
            description="Identify competitors for a brand. Input: brand name. $0.03.",
        ),
        Tool(
            name="content_gaps",
            func=lambda topic="": _call("get_content_gaps", topic=topic),
            description="Find content gaps in a topic area. Input: topic. $0.03. Example: content_gaps('DeFi lending')",
        ),
        Tool(
            name="whale_tracker",
            func=lambda symbol="BTC", hours="24": _call("get_whales", symbol=symbol, hours=hours),
            description="Track large crypto transactions (whales). Input: symbol, hours. $0.02. Example: whale_tracker('BTC', '24')",
        ),
        Tool(
            name="exchange_flows",
            func=lambda symbol="BTC", hours="24": _call("get_exchange_flows", symbol=symbol, hours=hours),
            description="Track exchange inflows/outflows. Input: symbol, hours. $0.02.",
        ),
        Tool(
            name="defi_tvl",
            func=lambda chain="": _call("get_defi_tvl", chain=chain or None),
            description="Get Total Value Locked across DeFi protocols. Input: chain or empty. $0.02.",
        ),
        Tool(
            name="npm_stats",
            func=lambda package="": _call("get_npm_stats", package=package),
            description="Get npm package download statistics. Input: package name. $0.02. Example: npm_stats('langchain')",
        ),
        Tool(
            name="github_trending",
            func=lambda language="", since="daily": _call("get_github_trending", language=language, since=since),
            description="Get trending GitHub repositories. Input: language, since (daily/weekly/monthly). $0.02.",
        ),
        Tool(
            name="token_risk",
            func=lambda symbol="BTC": _call("get_token_risk", symbol=symbol),
            description="Get risk assessment for a crypto token (volatility, liquidity, smart contract risk). Input: symbol. $0.03.",
        ),
        Tool(
            name="crypto_signals",
            func=lambda symbol="BTC": _call("get_crypto_signals", symbol=symbol),
            description="Get aggregated trading signals for a crypto symbol (buy/sell/hold). Input: symbol. $0.04.",
        ),
        Tool(
            name="yield_comparison",
            func=lambda symbol="USDC": _call("get_yield_comparison", symbol=symbol),
            description="Compare yields for a token across protocols. Input: token symbol. $0.03.",
        ),
        Tool(
            name="portfolio_intelligence",
            func=lambda symbol="BTC": _call("get_portfolio_intelligence", symbol=symbol),
            description="Get portfolio intelligence report: price + technical signal + risk score + market sentiment + verdict. Input: symbol. $0.10.",
        ),
        Tool(
            name="defi_strategy",
            func=lambda chain="": _call("get_defi_strategy", chain=chain or None),
            description="Get DeFi investment strategy: top yields + protocol TVL + cross-chain comparison + risk assessment. Input: chain or empty. $0.25.",
        ),
        Tool(
            name="market_pulse",
            func=lambda: _call("get_market_pulse"),
            description="Get market pulse: Fear & Greed + trending + news + social + whale activity + global overview. No input. $0.05.",
        ),
        Tool(
            name="onchain_overview",
            func=lambda symbol="BTC", hours="24": _call("get_onchain_overview", symbol=symbol, hours=hours),
            description="Get on-chain analytics: whales + exchange flows + stablecoin flows + correlation + DeFi TVL. Input: symbol, hours. $0.15.",
        ),
        Tool(
            name="deep_research",
            func=lambda query="": _call("deep_research", query=query),
            description="Deep research: web search + extract + synthesize into comprehensive report. Input: research query. $0.05. Example: deep_research('Bitcoin halving impact on DeFi')",
        ),
        Tool(
            name="ai_inference",
            func=lambda prompt="", model="gpt-5.4-mini": _call("inference", prompt=prompt, model=model),
            description="Run AI inference (GPT models). Input: prompt, model name. $0.03. Example: ai_inference('Summarize the latest BTC price action')",
        ),
        Tool(
            name="ai_complete",
            func=lambda prompt="", model="gpt-5.4-mini": _call("complete", prompt=prompt, model=model),
            description="AI text completion. Input: prompt, model. $0.03. Example: ai_complete('Write a tweet about')",
        ),
        Tool(
            name="fx_rates",
            func=lambda base="USD": _call("get_fx_rates", base=base),
            description="Get foreign exchange rates. Input: base currency. $0.01.",
        ),
        Tool(
            name="web_extract",
            func=lambda url="": _call("web_extract", url=url),
            description="Extract clean text content from a web page. Input: URL. $0.01.",
        ),
        Tool(
            name="stock_quote",
            func=lambda symbol="AAPL": _call("get_stock_quote", symbol=symbol),
            description="Get stock price quote. Input: ticker symbol. $0.01.",
        ),
        Tool(
            name="stock_history",
            func=lambda symbol="AAPL", period="1mo": _call("get_stock_history", symbol=symbol, period=period),
            description="Get stock price history. Input: symbol, period (1mo, 3mo, 1y). $0.01.",
        ),
        Tool(
            name="commodities",
            func=lambda: _call("get_commodities"),
            description="Get commodity prices (gold, silver, oil). No input. $0.02.",
        ),
    ]

    if endpoints:
        all_tools = [t for t in all_tools if t.name in endpoints]

    return all_tools
