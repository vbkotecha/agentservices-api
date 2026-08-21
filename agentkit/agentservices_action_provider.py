"""
AgentServices Action Provider for Coinbase AgentKit.

Provides AI agents with access to AgentServices' 50+ data APIs.
Free endpoints work out of the box. Paid endpoints use x402 (USDC on Base).

Usage:
    from coinbase_agentkit import AgentKit, AgentKitConfig
    from agentkit import agentservices_action_provider

    agent_kit = AgentKit(AgentKitConfig(
        wallet_provider=wallet_provider,
        action_providers=[
            agentservices_action_provider(),
        ]
    ))
"""

import json
import requests
from typing import Any
from pydantic import BaseModel, Field

from coinbase_agentkit import ActionProvider, WalletProvider, create_action
from coinbase_agentkit.network import Network

AGENTSERVICES_BASE_URL = "https://agentservices.to"


# ============================================================================
# Input Schemas
# ============================================================================

class GetCryptoPriceSchema(BaseModel):
    symbol: str = Field(..., description="Crypto symbol (e.g., BTC, ETH, SOL)")

class GetBatchPricesSchema(BaseModel):
    symbols: str = Field(..., description="Comma-separated symbols (e.g., BTC,ETH,SOL)")

class GetIndicatorsSchema(BaseModel):
    symbol: str = Field(..., description="Crypto symbol (e.g., BTC)")

class GetDefiYieldsSchema(BaseModel):
    limit: int = Field(default=10, description="Max results (default 10)")

class GetFearGreedSchema(BaseModel):
    pass

class GetTrendingSchema(BaseModel):
    pass

class GetGasSchema(BaseModel):
    pass

class GetGlobalMarketSchema(BaseModel):
    pass

class GetPortfolioSchema(BaseModel):
    symbol: str = Field(..., description="Crypto symbol for portfolio analysis (e.g., BTC)")

class GetMarketPulseSchema(BaseModel):
    pass

class GetResearchSchema(BaseModel):
    query: str = Field(..., description="Research query or topic to search and synthesize")
    max_results: int = Field(default=5, description="Max search results to synthesize (default 5)")

class GetDefiStrategySchema(BaseModel):
    risk_tolerance: str = Field(
        default="moderate",
        description="Risk tolerance: conservative, moderate, or aggressive"
    )

class GetOnchainOverviewSchema(BaseModel):
    pass

class SearchWebSchema(BaseModel):
    query: str = Field(..., description="Search query")
    num_results: int = Field(default=5, description="Number of results (default 5)")

class GetTokenRiskSchema(BaseModel):
    symbol: str = Field(..., description="Token symbol or contract address")

class GetCryptoSignalsSchema(BaseModel):
    symbol: str = Field(..., description="Crypto symbol (e.g., BTC)")

class GetInferenceSchema(BaseModel):
    prompt: str = Field(..., description="Prompt for AI inference (gpt-5.4/5.5)")
    model: str = Field(default="gpt-5.4-mini", description="Model: gpt-5.4, gpt-5.4-mini, or gpt-5.5")

class GetStockQuoteSchema(BaseModel):
    symbol: str = Field(..., description="Stock ticker (e.g., AAPL, GOOGL)")

class GetFxRatesSchema(BaseModel):
    base: str = Field(default="USD", description="Base currency (default USD)")


# ============================================================================
# Helper Functions
# ============================================================================

def _make_request(endpoint: str, params: dict = None) -> str:
    """Make GET request to AgentServices API. Returns JSON string."""
    url = f"{AGENTSERVICES_BASE_URL}{endpoint}"
    try:
        response = requests.get(url, params=params or {}, timeout=30)
        if response.status_code == 402:
            return json.dumps({
                "error": "Payment required",
                "message": (
                    "This endpoint requires x402 payment. "
                    "Use x402-enabled fetch to automatically pay with USDC on Base. "
                    "Install: pip install x402-fetch. "
                    "See https://agentservices.to/examples for payment setup."
                ),
                "payment_url": url,
            })
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": str(e)})


# ============================================================================
# Action Provider
# ============================================================================

class AgentServicesActionProvider(ActionProvider[WalletProvider]):
    """
    Action provider for AgentServices - 50+ paid APIs for AI agents.

    Free endpoints: crypto prices, fear-greed, trending, gas, global market.
    Paid endpoints ($0.003-$0.25): indicators, DeFi yields, portfolio intelligence,
    market pulse, research, onchain analytics, web search, AI inference, and more.
    Payments via x402 protocol (USDC on Base).
    """

    def __init__(self):
        super().__init__("agentservices", [])

    # --- FREE ENDPOINTS ---

    @create_action(
        name="get_crypto_price",
        description="Get current cryptocurrency price. Free endpoint. "
                    "Returns price, 24h change, market cap, and volume.",
        schema=GetCryptoPriceSchema,
    )
    def get_crypto_price(self, args: dict[str, Any]) -> str:
        """Get current price for a cryptocurrency."""
        return _make_request(f"/v1/price/{args['symbol'].upper()}")

    @create_action(
        name="get_batch_prices",
        description="Get prices for multiple cryptocurrencies at once. Free endpoint.",
        schema=GetBatchPricesSchema,
    )
    def get_batch_prices(self, args: dict[str, Any]) -> str:
        """Get batch crypto prices."""
        return _make_request("/v1/prices", {"symbols": args["symbols"].upper()})

    @create_action(
        name="get_fear_greed",
        description="Get the Crypto Fear & Greed Index (0-100). "
                    "0=Extreme Fear, 100=Extreme Greed. Free endpoint.",
        schema=GetFearGreedSchema,
    )
    def get_fear_greed(self, args: dict[str, Any]) -> str:
        """Get Crypto Fear & Greed Index."""
        return _make_request("/v1/fear-greed")

    @create_action(
        name="get_trending",
        description="Get trending cryptocurrencies being searched right now. Free endpoint.",
        schema=GetTrendingSchema,
    )
    def get_trending(self, args: dict[str, Any]) -> str:
        """Get trending cryptocurrencies."""
        return _make_request("/v1/trending")

    @create_action(
        name="get_gas_prices",
        description="Get current Ethereum gas prices (slow/standard/fast). Free endpoint.",
        schema=GetGasSchema,
    )
    def get_gas_prices(self, args: dict[str, Any]) -> str:
        """Get current Ethereum gas prices."""
        return _make_request("/v1/gas")

    @create_action(
        name="get_global_market",
        description="Get global crypto market cap, 24h volume, and BTC dominance. Free endpoint.",
        schema=GetGlobalMarketSchema,
    )
    def get_global_market(self, args: dict[str, Any]) -> str:
        """Get global crypto market data."""
        return _make_request("/v1/global")

    # --- PAID ENDPOINTS ($0.003-$0.25 via x402) ---

    @create_action(
        name="get_market_indicators",
        description="Get technical indicators for a cryptocurrency (RSI, MACD, Bollinger "
                    "Bands, moving averages). Paid: $0.02 via x402.",
        schema=GetIndicatorsSchema,
    )
    def get_market_indicators(self, args: dict[str, Any]) -> str:
        """Get technical indicators for a crypto asset."""
        return _make_request(f"/v1/indicators/{args['symbol'].upper()}")

    @create_action(
        name="get_defi_yields",
        description="Get top DeFi yield opportunities across protocols. "
                    "Returns APY, TVL, protocol, chain, and risk level. Paid: $0.02 via x402.",
        schema=GetDefiYieldsSchema,
    )
    def get_defi_yields(self, args: dict[str, Any]) -> str:
        """Get top DeFi yield opportunities."""
        return _make_request("/v1/defi/yields", {"limit": args.get("limit", 10)})

    @create_action(
        name="get_portfolio_intelligence",
        description="Comprehensive portfolio analysis for a crypto asset. Aggregates price, "
                    "technical signals, risk score, and market sentiment with a synthesized "
                    "verdict. Paid: $0.10 via x402.",
        schema=GetPortfolioSchema,
    )
    def get_portfolio_intelligence(self, args: dict[str, Any]) -> str:
        """Get comprehensive portfolio intelligence report."""
        return _make_request("/v1/portfolio", {"symbol": args["symbol"].upper()})

    @create_action(
        name="get_market_pulse",
        description="Get a comprehensive crypto market overview aggregating Fear & Greed, "
                    "trending tokens, news, social sentiment, whale movements, and global "
                    "metrics into a synthesized market direction signal. Paid: $0.05 via x402.",
        schema=GetMarketPulseSchema,
    )
    def get_market_pulse(self, args: dict[str, Any]) -> str:
        """Get synthesized market pulse report."""
        return _make_request("/v1/market-pulse")

    @create_action(
        name="get_deep_research",
        description="Deep research on any topic. Searches the web, extracts key content, "
                    "and synthesizes a comprehensive report. Returns analysis, key findings, "
                    "and sources. Paid: $0.05 via x402.",
        schema=GetResearchSchema,
    )
    def get_deep_research(self, args: dict[str, Any]) -> str:
        """Get deep research report on any topic."""
        return _make_request(
            "/v1/research",
            {"query": args["query"], "max_results": args.get("max_results", 5)},
        )

    @create_action(
        name="get_defi_strategy",
        description="Generate a DeFi investment strategy report. Aggregates top yields, "
                    "protocol TVL analysis, cross-chain comparison, and risk assessment "
                    "with high-APY flags. Specify risk tolerance. Paid: $0.25 via x402.",
        schema=GetDefiStrategySchema,
    )
    def get_defi_strategy(self, args: dict[str, Any]) -> str:
        """Get DeFi investment strategy report."""
        return _make_request(
            "/v1/defi-strategy",
            {"risk": args.get("risk_tolerance", "moderate")},
        )

    @create_action(
        name="get_onchain_overview",
        description="Comprehensive onchain analytics report aggregating whale movements, "
                    "exchange flows, stablecoin flows, correlation matrix, and DeFi TVL "
                    "into a single market intelligence view. Paid: $0.15 via x402.",
        schema=GetOnchainOverviewSchema,
    )
    def get_onchain_overview(self, args: dict[str, Any]) -> str:
        """Get onchain analytics overview."""
        return _make_request("/v1/onchain-overview")

    @create_action(
        name="search_web",
        description="Search the web and return results with titles, URLs, and snippets. "
                    "Paid: $0.01 per call via x402.",
        schema=SearchWebSchema,
    )
    def search_web(self, args: dict[str, Any]) -> str:
        """Search the web."""
        return _make_request(
            "/v1/search",
            {"q": args["query"], "num": args.get("num_results", 5)},
        )

    @create_action(
        name="get_token_risk",
        description="Get risk assessment for a crypto token including rug/honeypot checks, "
                    "liquidity analysis, and contract audit status. Paid: $0.03 via x402.",
        schema=GetTokenRiskSchema,
    )
    def get_token_risk(self, args: dict[str, Any]) -> str:
        """Get token risk assessment."""
        return _make_request("/v1/token-risk", {"token": args["symbol"]})

    @create_action(
        name="get_crypto_signals",
        description="Get aggregated trading signals for a cryptocurrency combining "
                    "technical indicators, onchain metrics, and market sentiment into "
                    "buy/sell/hold recommendations. Paid: $0.04 via x402.",
        schema=GetCryptoSignalsSchema,
    )
    def get_crypto_signals(self, args: dict[str, Any]) -> str:
        """Get aggregated crypto trading signals."""
        return _make_request("/v1/crypto-signals", {"symbol": args["symbol"].upper()})

    @create_action(
        name="get_ai_inference",
        description="Run AI inference using GPT-5.4 or GPT-5.5 models. Supports any text "
                    "generation task - analysis, summarization, code generation, Q&A. "
                    "Paid: $0.03 via x402.",
        schema=GetInferenceSchema,
    )
    def get_ai_inference(self, args: dict[str, Any]) -> str:
        """Run AI inference."""
        return _make_request(
            "/v1/inference",
            {"prompt": args["prompt"], "model": args.get("model", "gpt-5.4-mini")},
        )

    @create_action(
        name="get_stock_quote",
        description="Get stock market quote for any ticker symbol. Returns price, change, "
                    "volume, P/E, market cap, and more. Paid: $0.01 via x402.",
        schema=GetStockQuoteSchema,
    )
    def get_stock_quote(self, args: dict[str, Any]) -> str:
        """Get stock market quote."""
        return _make_request(f"/v1/stock/{args['symbol'].upper()}/quote")

    @create_action(
        name="get_fx_rates",
        description="Get foreign exchange rates for 30+ currencies. Specify base currency. "
                    "Paid: $0.003 via x402.",
        schema=GetFxRatesSchema,
    )
    def get_fx_rates(self, args: dict[str, Any]) -> str:
        """Get FX rates."""
        return _make_request("/v1/fx", {"base": args.get("base", "USD")})

    def supports_network(self, network: Network) -> bool:
        """AgentServices works on any network - data APIs are network-agnostic."""
        return True


def agentservices_action_provider():
    """Create and return an AgentServices action provider instance."""
    return AgentServicesActionProvider()
