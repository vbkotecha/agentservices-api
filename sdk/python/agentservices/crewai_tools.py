"""
CrewAI Tool Wrappers for AgentServices
=======================================
Native CrewAI BaseTool subclasses for AgentServices endpoints.

Usage:
    from agentservices import create_crewai_tools
    tools = create_crewai_tools()
    agent = Agent(role='Crypto Analyst', tools=tools, llm=llm)
"""
import json
from typing import Optional, List, Type
from pydantic import BaseModel, Field

from .client import AgentServicesClient
from .langchain_tools import _safe_json, _get_client

def create_crewai_tools(
    wallet_private_key: Optional[str] = None,
    base_url: Optional[str] = None,
    endpoints: Optional[List[str]] = None,
) -> list:
    """
    Create CrewAI BaseTool objects for AgentServices endpoints.

    Args:
        wallet_private_key: EVM private key for x402 auto-pay (optional)
        base_url: Override API base URL
        endpoints: List of endpoint names to include (default: all)

    Returns:
        List of CrewAI BaseTool objects
    """
    try:
        from crewai.tools import BaseTool
    except ImportError:
        try:
            from crewai_tools import BaseTool
        except ImportError:
            raise ImportError("crewai is required: pip install crewai")

    _get_client(wallet_private_key, base_url)
    client = _get_client()

    class CryptoPricesTool(BaseTool):
        name: str = "crypto_prices"
        description: str = "Get current crypto prices. Input: comma-separated symbols like 'BTC,ETH,XRP'. FREE."
        def _run(self, symbols: str = "BTC,ETH") -> str:
            return _safe_json(client.get_prices(symbols))

    class TechnicalIndicatorsTool(BaseTool):
        name: str = "technical_indicators"
        description: str = "Get technical indicators (RSI, MACD, Bollinger Bands) for a crypto symbol. Input: symbol. $0.02."
        def _run(self, symbol: str, interval: str = "1d") -> str:
            return _safe_json(client.get_indicators(symbol, interval))

    class DefiYieldsTool(BaseTool):
        name: str = "defi_yields"
        description: str = "Get DeFi yield rates across protocols. Input: chain name or empty for all. $0.02."
        def _run(self, chain: str = "") -> str:
            return _safe_json(client.get_defi_yields(chain or None))

    class FearGreedTool(BaseTool):
        name: str = "fear_greed_index"
        description: str = "Get crypto Fear & Greed sentiment index. No input needed. FREE."
        def _run(self) -> str:
            return _safe_json(client.get_fear_greed())

    class IPGeolocationTool(BaseTool):
        name: str = "ip_geolocation"
        description: str = "Get geolocation for an IP address. Input: IP or empty for own. FREE."
        def _run(self, ip: str = "") -> str:
            return _safe_json(client.get_geo(ip or None))

    class URLMetadataTool(BaseTool):
        name: str = "url_metadata"
        description: str = "Extract metadata from a URL. Input: full URL. $0.01."
        def _run(self, url: str) -> str:
            return _safe_json(client.get_url_metadata(url))

    class SearchTool(BaseTool):
        name: str = "crypto_search"
        description: str = "Search the web for crypto/blockchain information. Input: query. $0.01."
        def _run(self, query: str) -> str:
            return _safe_json(client.search(query))

    class TrendingTool(BaseTool):
        name: str = "trending_tokens"
        description: str = "Get trending crypto tokens. No input. FREE."
        def _run(self) -> str:
            return _safe_json(client.get_trending())

    class GasTool(BaseTool):
        name: str = "gas_tracker"
        description: str = "Get current gas prices across chains. Input: chain or empty. FREE."
        def _run(self, chain: str = "") -> str:
            return _safe_json(client.get_gas(chain or None))

    class NewsTool(BaseTool):
        name: str = "crypto_news"
        description: str = "Get latest crypto news headlines. No input. FREE."
        def _run(self) -> str:
            return _safe_json(client.get_news())

    class PortfolioIntelligenceTool(BaseTool):
        name: str = "portfolio_intelligence"
        description: str = "Get portfolio report: price + signal + risk + sentiment + verdict. Input: symbol. $0.10."
        def _run(self, symbol: str = "BTC") -> str:
            return _safe_json(client.get_portfolio_intelligence(symbol))

    class DefiStrategyTool(BaseTool):
        name: str = "defi_strategy"
        description: str = "Get DeFi investment strategy report. Input: chain or empty. $0.25."
        def _run(self, chain: str = "") -> str:
            return _safe_json(client.get_defi_strategy(chain or None))

    class MarketPulseTool(BaseTool):
        name: str = "market_pulse"
        description: str = "Get market overview: Fear&Greed + trending + news + social + whales. No input. $0.05."
        def _run(self) -> str:
            return _safe_json(client.get_market_pulse())

    class OnchainOverviewTool(BaseTool):
        name: str = "onchain_overview"
        description: str = "Get on-chain analytics: whales + flows + correlation + TVL. Input: symbol, hours. $0.15."
        def _run(self, symbol: str = "BTC", hours: str = "24") -> str:
            return _safe_json(client.get_onchain_overview(symbol, hours))

    class DeepResearchTool(BaseTool):
        name: str = "deep_research"
        description: str = "Deep research: search + extract + synthesize. Input: query. $0.05."
        def _run(self, query: str) -> str:
            return _safe_json(client.deep_research(query))

    class AIInferenceTool(BaseTool):
        name: str = "ai_inference"
        description: str = "Run AI inference (GPT models). Input: prompt. $0.03."
        def _run(self, prompt: str, model: str = "gpt-5.4-mini") -> str:
            return _safe_json(client.inference(prompt, model))

    class TokenRiskTool(BaseTool):
        name: str = "token_risk"
        description: str = "Get risk assessment for a crypto token. Input: symbol. $0.03."
        def _run(self, symbol: str) -> str:
            return _safe_json(client.get_token_risk(symbol))

    class CryptoSignalsTool(BaseTool):
        name: str = "crypto_signals"
        description: str = "Get aggregated trading signals (buy/sell/hold). Input: symbol. $0.04."
        def _run(self, symbol: str) -> str:
            return _safe_json(client.get_crypto_signals(symbol))

    class WhaleTrackerTool(BaseTool):
        name: str = "whale_tracker"
        description: str = "Track large crypto transactions. Input: symbol, hours. $0.02."
        def _run(self, symbol: str = "BTC", hours: str = "24") -> str:
            return _safe_json(client.get_whales(symbol, hours))

    class StockQuoteTool(BaseTool):
        name: str = "stock_quote"
        description: str = "Get stock price quote. Input: ticker. $0.01."
        def _run(self, symbol: str = "AAPL") -> str:
            return _safe_json(client.get_stock_quote(symbol))

    all_tools = [
        CryptoPricesTool(), TechnicalIndicatorsTool(), DefiYieldsTool(),
        FearGreedTool(), IPGeolocationTool(), URLMetadataTool(), SearchTool(),
        TrendingTool(), GasTool(), NewsTool(), PortfolioIntelligenceTool(),
        DefiStrategyTool(), MarketPulseTool(), OnchainOverviewTool(),
        DeepResearchTool(), AIInferenceTool(), TokenRiskTool(), CryptoSignalsTool(),
        WhaleTrackerTool(), StockQuoteTool(),
    ]

    if endpoints:
        all_tools = [t for t in all_tools if t.name in endpoints]

    return all_tools
