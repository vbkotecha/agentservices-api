"""MCP tool pricing — mirrors x402 REST route prices for credit deduction."""

from decimal import Decimal

# Free MCP tools (no payment required for wallet or human paths)
FREE_MCP_TOOLS = frozenset({
    "crypto_prices",
    "fear_greed",
    "ip_geolocation",
    "list_policies",
    "agent_context",
    "marketing_sentiment",
    "marketing_trends",
    "marketing_ad_copy",
    "buy_credits",
    "credit_balance",
})

# USD price per MCP tool — aligned with payment_routes in main.py
MCP_TOOL_PRICES: dict[str, Decimal] = {
    "technical_indicators": Decimal("0.02"),
    "defi_yields": Decimal("0.02"),
    "url_metadata": Decimal("0.01"),
    "resolve_dispute": Decimal("0.05"),
    "whale_tracking": Decimal("0.02"),
    "exchange_flows": Decimal("0.02"),
    "correlation_matrix": Decimal("0.03"),
    "defi_tvl": Decimal("0.02"),
    "stablecoin_flows": Decimal("0.02"),
    "github_velocity": Decimal("0.02"),
    "macro_indicators": Decimal("0.02"),
    "llm_inference": Decimal("0.03"),
    "token_risk": Decimal("0.03"),
    "crypto_signals": Decimal("0.04"),
    "stock_quote": Decimal("0.02"),
    "stock_history": Decimal("0.03"),
    "sec_filings": Decimal("0.03"),
    "commodities": Decimal("0.03"),
    "fx_rates": Decimal("0.003"),
    "web_extract": Decimal("0.002"),
    "package_security": Decimal("0.02"),
    "seo_keywords": Decimal("0.01"),
    "deep_research": Decimal("0.05"),
    "portfolio_intelligence": Decimal("0.10"),
    "defi_strategy": Decimal("0.25"),
    "market_pulse": Decimal("0.05"),
    "onchain_overview": Decimal("0.15"),
    "arbitrage_scanner": Decimal("0.08"),
    "liquidation_map": Decimal("0.12"),
    "chat": Decimal("0.03"),
    "generate_image": Decimal("0.05"),
    "text_to_speech": Decimal("0.05"),
}


def tool_price_usd(tool_name: str) -> Decimal | None:
    """Return USD price for a paid MCP tool, or None if free/unknown."""
    if tool_name in FREE_MCP_TOOLS:
        return None
    return MCP_TOOL_PRICES.get(tool_name)


def is_paid_mcp_tool(tool_name: str) -> bool:
    return tool_price_usd(tool_name) is not None
