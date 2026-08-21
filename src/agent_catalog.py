"""Task-oriented discovery catalog for AgentServices.

This is an original implementation of the useful Treg product pattern: agents
search by outcome, inspect a quote and call contract, then invoke a known
AgentServices route. It does not proxy arbitrary third-party URLs or handle
provider credentials.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CatalogTool:
    id: str
    name: str
    description: str
    method: str
    path: str
    price_usd: float
    tags: tuple[str, ...]
    status: str = "active"

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["tags"] = list(self.tags)
        value["estimated_cost_usd"] = value.pop("price_usd")
        return value


# Keep this list deliberately limited to routes that exist in this service.
# It is a discovery index, not a claim that external providers are connected.
TOOLS: tuple[CatalogTool, ...] = (
    CatalogTool("crypto.price", "Crypto price", "Current price for a crypto asset", "GET", "/v1/price/{symbol}", 0.0, ("crypto", "market-data")),
    CatalogTool("crypto.prices", "Crypto prices", "Batch prices for multiple crypto assets", "GET", "/v1/prices", 0.0, ("crypto", "market-data")),
    CatalogTool("crypto.indicators", "Technical indicators", "RSI, MACD, Bollinger Bands, ATR and support/resistance", "GET", "/v1/indicators/{symbol}", 0.02, ("crypto", "technical-analysis")),
    CatalogTool("crypto.token-risk", "Token risk", "Risk score and dimensions for a token", "GET", "/v1/token-risk/{symbol}", 0.03, ("crypto", "risk")),
    CatalogTool("crypto.market-pulse", "Market pulse", "Sentiment, trends, news, whales and global market context", "GET", "/v1/market-pulse", 0.05, ("crypto", "research")),
    CatalogTool("research.web", "Web research", "Search and synthesize live web sources", "GET", "/v1/research", 0.05, ("research", "web")),
    CatalogTool("research.extract", "Web extraction", "Extract clean content from a URL", "POST", "/v1/web-extract", 0.002, ("research", "web")),
    CatalogTool("finance.stock-quote", "Stock quote", "Current quote for a listed stock", "GET", "/v1/stock-quote", 0.02, ("finance", "markets")),
    CatalogTool("finance.fx", "FX rates", "Foreign-exchange rates across supported currencies", "GET", "/v1/fx", 0.003, ("finance", "markets")),
    CatalogTool("developer.package-security", "Package security", "Dependency vulnerability and security scan", "GET", "/v1/security/{package}", 0.02, ("developer", "security")),
    CatalogTool("inference.chat", "Chat completion", "Model-routed chat completion with an x402 quote", "POST", "/v1/chat/completions", 0.003, ("inference", "models")),
    CatalogTool("media.image", "Image generation", "Generate an image from a prompt", "POST", "/v1/images/generations", 0.05, ("media", "generation")),
    CatalogTool("media.speech", "Text to speech", "Generate speech from text", "POST", "/v1/audio/speech", 0.05, ("media", "generation")),
)


def search_catalog(query: str = "", tags: list[str] | None = None, limit: int = 25) -> list[dict[str, Any]]:
    terms = {part.lower() for part in query.split() if part.strip()}
    wanted = {tag.lower() for tag in (tags or [])}
    matches: list[dict[str, Any]] = []
    for tool in TOOLS:
        haystack = " ".join((tool.id, tool.name, tool.description, *tool.tags)).lower()
        if terms and not all(term in haystack for term in terms):
            continue
        if wanted and not wanted.intersection(tool.tags):
            continue
        matches.append(tool.as_dict())
    return matches[: max(1, min(limit, 100))]


def get_tool(tool_id: str) -> dict[str, Any] | None:
    for tool in TOOLS:
        if tool.id == tool_id:
            return tool.as_dict()
    return None
