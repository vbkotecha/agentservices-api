"""
AgentServices API Client
========================
Comprehensive async + sync client for all AgentServices x402 endpoints.
Handles 402 payment-required responses gracefully.
"""
import json
import httpx
from typing import Optional, Dict, Any, List, Union


BASE_URL = "https://agentservices.to"


class PaymentRequired(Exception):
    """Raised when a paid endpoint returns 402 and no wallet is configured."""
    def __init__(self, response_data: dict):
        self.data = response_data
        self.amount = None
        self.networks = []
        accepts = response_data.get("accepts", [])
        if accepts:
            first = accepts[0]
            self.amount = first.get("maxAmountRequired")
            scheme = first.get("scheme", "")
            self.networks.append(scheme)
        super().__init__(
            f"Payment required: {self.amount} units via {', '.join(self.networks) if self.networks else 'x402'}. "
            f"Configure AgentServicesClient(wallet_private_key=...) to auto-pay."
        )


class AgentServicesClient:
    """Client for all AgentServices endpoints (50 services, 38 paid via x402)."""

    def __init__(
        self,
        base_url: str = BASE_URL,
        wallet_private_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._wallet_pk = wallet_private_key
        self._sync_client: Optional[httpx.Client] = None
        self._async_client: Optional[httpx.AsyncClient] = None

    def _get_sync_client(self) -> httpx.Client:
        if self._sync_client is None:
            self._sync_client = httpx.Client(timeout=self.timeout)
        return self._sync_client

    async def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(timeout=self.timeout)
        return self._async_client

    def _handle_response(self, r: httpx.Response) -> Any:
        """Handle response, detecting 402 payment requirements."""
        if r.status_code == 402:
            try:
                data = r.json()
            except Exception:
                data = {"raw": r.text}
            raise PaymentRequired(data)
        r.raise_for_status()
        return r.json()

    def _request(
        self, method: str, path: str, params: Optional[dict] = None, json_body: Optional[dict] = None
    ) -> Any:
        client = self._get_sync_client()
        url = f"{self.base_url}{path}"
        r = client.request(method, url, params=params, json=json_body)
        return self._handle_response(r)

    async def _arequest(
        self, method: str, path: str, params: Optional[dict] = None, json_body: Optional[dict] = None
    ) -> Any:
        client = await self._get_async_client()
        url = f"{self.base_url}{path}"
        r = await client.request(method, url, params=params, json=json_body)
        return self._handle_response(r)

    # ==================== FREE ENDPOINTS ====================

    def get_prices(self, symbols: Optional[str] = None) -> Dict:
        """Get current crypto prices. Input: comma-separated like 'BTC,ETH'. FREE."""
        params = {"symbols": symbols} if symbols else {}
        return self._request("GET", "/v1/prices", params=params)

    def get_fear_greed(self) -> Dict:
        """Get crypto Fear & Greed sentiment index. FREE."""
        return self._request("GET", "/v1/fear-greed")

    def get_geo(self, ip: Optional[str] = None) -> Dict:
        """Get IP geolocation. Input: IP address. FREE."""
        params = {"ip": ip} if ip else {}
        return self._request("GET", "/v1/geo", params=params)

    def get_trending(self) -> Dict:
        """Get trending crypto tokens. FREE."""
        return self._request("GET", "/v1/trending")

    def get_gas(self, chain: str = "ethereum") -> Dict:
        """Get current gas prices. Input: chain name. FREE."""
        return self._request("GET", "/v1/gas", params={"chain": chain})

    def get_swap_quote(self, chain: str, token_in: str, token_out: str, amount: str) -> Dict:
        """Get DEX swap quote. FREE."""
        return self._request("GET", "/v1/swap/quote", params={
            "chain": chain, "token_in": token_in, "token_out": token_out, "amount": amount
        })

    def get_predictions(self, symbol: str) -> Dict:
        """Get crypto price predictions. FREE."""
        return self._request("GET", "/v1/predictions", params={"symbol": symbol})

    def get_news(self, category: str = "crypto", limit: int = 10) -> Dict:
        """Get latest crypto/tech news. FREE."""
        return self._request("GET", "/v1/news", params={"category": category, "limit": limit})

    def get_social_trending(self) -> Dict:
        """Get trending social topics for crypto. FREE."""
        return self._request("GET", "/v1/social/trending")

    def get_global_market(self) -> Dict:
        """Get global crypto market cap, volume, dominance. FREE."""
        return self._request("GET", "/v1/global")

    def list_policies(self) -> List[Dict]:
        """List dispute resolution policy templates. FREE."""
        return self._request("GET", "/v1/policies")

    def get_stock_quote(self, symbol: str) -> Dict:
        """Get stock price quote. FREE."""
        return self._request("GET", "/v1/stock/quote", params={"symbol": symbol})

    def get_commodities(self) -> Dict:
        """Get commodity prices (gold, silver, oil). FREE."""
        return self._request("GET", "/v1/commodities")

    def get_fx_rates(self) -> Dict:
        """Get foreign exchange rates. FREE."""
        return self._request("GET", "/v1/fx-rates")

    # ==================== PAID ENDPOINTS ($0.01 - $0.05) ====================

    def search(self, query: str, num_results: int = 5) -> Dict:
        """Web search optimized for agents. $0.01 x402."""
        return self._request("GET", "/v1/search", params={"q": query, "num": num_results})

    def get_indicators(self, symbol: str, interval: str = "1d") -> Dict:
        """Get technical indicators (RSI, MACD, BB). $0.02 x402."""
        return self._request("GET", "/v1/indicators", params={"symbol": symbol, "interval": interval})

    def get_defi_yields(self, chain: Optional[str] = None) -> Dict:
        """Get DeFi yield rates across protocols. $0.02 x402."""
        params = {"chain": chain} if chain else {}
        return self._request("GET", "/v1/defi/yields", params=params)

    def get_url_metadata(self, url: str) -> Dict:
        """Extract metadata from a URL (title, description, OG tags). $0.01 x402."""
        return self._request("GET", "/v1/metadata", params={"url": url})

    def get_token_risk(self, address: str, chain: str = "ethereum") -> Dict:
        """Assess token risk (honeypot, liquidity, contract). $0.03 x402."""
        return self._request("GET", "/v1/token-risk", params={"address": address, "chain": chain})

    def get_crypto_signals(self, symbol: str) -> Dict:
        """Get aggregated crypto trading signals. $0.04 x402."""
        return self._request("GET", "/v1/crypto-signals", params={"symbol": symbol})

    def get_yield_comparison(self, chain: Optional[str] = None) -> Dict:
        """Compare DeFi yields across chains and protocols. $0.03 x402."""
        params = {"chain": chain} if chain else {}
        return self._request("GET", "/v1/yield-comparison", params=params)

    def get_hn_sentiment(self, topic: str) -> Dict:
        """Analyze Hacker News sentiment on a topic. $0.02 x402."""
        return self._request("GET", "/v1/hn-sentiment", params={"topic": topic})

    def get_npm_stats(self, package: str) -> Dict:
        """Get npm package download stats. $0.02 x402."""
        return self._request("GET", "/v1/npm-stats", params={"package": package})

    def get_github_trending(self, language: str = "", since: str = "weekly") -> Dict:
        """Get GitHub trending repos. $0.02 x402."""
        return self._request("GET", "/v1/github-trending", params={"language": language, "since": since})

    def get_github_velocity(self, repo: str) -> Dict:
        """Analyze GitHub repo commit velocity. $0.02 x402."""
        return self._request("GET", "/v1/github-velocity", params={"repo": repo})

    def get_web_extract(self, url: str) -> Dict:
        """Extract clean text content from a URL. $0.01 x402."""
        return self._request("GET", "/v1/web-extract", params={"url": url})

    def get_package_security(self, package: str, ecosystem: str = "npm") -> Dict:
        """Audit package security vulnerabilities. $0.02 x402."""
        return self._request("GET", "/v1/package-security", params={"package": package, "ecosystem": ecosystem})

    def get_seo_keywords(self, domain: str) -> Dict:
        """Analyze SEO keywords for a domain. $0.02 x402."""
        return self._request("GET", "/v1/seo-keywords", params={"domain": domain})

    def get_stock_history(self, symbol: str, period: str = "1mo") -> Dict:
        """Get stock price history. $0.02 x402."""
        return self._request("GET", "/v1/stock/history", params={"symbol": symbol, "period": period})

    def get_sec_filings(self, ticker: str, filing_type: str = "10-K") -> Dict:
        """Get SEC filings for a company. $0.02 x402."""
        return self._request("GET", "/v1/sec-filings", params={"ticker": ticker, "type": filing_type})

    def get_economic_indicators(self) -> Dict:
        """Get macro economic indicators (GDP, CPI, unemployment). $0.02 x402."""
        return self._request("GET", "/v1/economic-indicators")

    def get_agent_context(self, topic: str) -> Dict:
        """Get AI-optimized context summary on any topic. $0.02 x402."""
        return self._request("GET", "/v1/agent-context", params={"topic": topic})

    # ==================== PAID ENDPOINTS ($0.03 - $0.05) ====================

    def get_marketing_sentiment(self, brand: str) -> Dict:
        """Analyze brand sentiment across platforms. $0.03 x402."""
        return self._request("GET", "/v1/marketing/sentiment", params={"brand": brand})

    def get_marketing_trends(self, industry: str) -> Dict:
        """Get marketing trends for an industry. $0.03 x402."""
        return self._request("GET", "/v1/marketing/trends", params={"industry": industry})

    def get_marketing_competitors(self, domain: str) -> Dict:
        """Analyze competitors for a domain. $0.05 x402."""
        return self._request("GET", "/v1/marketing/competitors", params={"domain": domain})

    def get_marketing_content_gaps(self, domain: str) -> Dict:
        """Find content gaps for a domain. $0.05 x402."""
        return self._request("GET", "/v1/marketing/content-gaps", params={"domain": domain})

    def get_marketing_ad_copy(self, product: str, audience: str = "") -> Dict:
        """Generate AI ad copy. $0.03 x402."""
        return self._request("GET", "/v1/marketing/ad-copy", params={"product": product, "audience": audience})

    def get_deep_research(self, query: str) -> Dict:
        """Deep research with AI synthesis. $0.02 x402."""
        return self._request("GET", "/v1/deep-research", params={"query": query})

    def get_research(self, query: str) -> Dict:
        """Search + extract + synthesize in one call. $0.05 x402."""
        return self._request("GET", "/v1/research", params={"query": query})

    def get_market_pulse(self) -> Dict:
        """Market overview: fear-greed + trending + news + social + whales + global. $0.05 x402."""
        return self._request("GET", "/v1/market-pulse")

    # ==================== PAID ENDPOINTS ($0.10 - $0.25) ====================

    def get_portfolio_intelligence(self, symbol: str) -> Dict:
        """Price + signal + risk + sentiment + verdict. $0.10 x402."""
        return self._request("GET", "/v1/portfolio", params={"symbol": symbol})

    def get_onchain_overview(self, chain: str = "ethereum") -> Dict:
        """Whales + exchange flows + stablecoin flows + correlation + TVL. $0.15 x402."""
        return self._request("GET", "/v1/onchain-overview", params={"chain": chain})

    def get_defi_strategy(self, chain: Optional[str] = None) -> Dict:
        """Top yields + TVL + comparison + risk assessment. $0.25 x402."""
        params = {"chain": chain} if chain else {}
        return self._request("GET", "/v1/defi-strategy", params=params)

    # ==================== PAID ENDPOINTS — ON-CHAIN ANALYTICS ====================

    def get_whales(self, chain: str = "ethereum", limit: int = 10) -> Dict:
        """Track large transactions. $0.02 x402."""
        return self._request("GET", "/v1/whales", params={"chain": chain, "limit": limit})

    def get_exchange_flows(self, chain: str = "ethereum") -> Dict:
        """Exchange inflow/outflow data. $0.02 x402."""
        return self._request("GET", "/v1/exchange-flows", params={"chain": chain})

    def get_correlation(self, symbols: str = "BTC,ETH,XRP,SOL") -> Dict:
        """Correlation matrix for crypto assets. $0.02 x402."""
        return self._request("GET", "/v1/correlation", params={"symbols": symbols})

    def get_stablecoin_flows(self) -> Dict:
        """Stablecoin mint/burn flows. $0.02 x402."""
        return self._request("GET", "/v1/stablecoin-flows")

    def get_defi_tvl(self, chain: Optional[str] = None) -> Dict:
        """DeFi TVL by protocol and chain. $0.02 x402."""
        params = {"chain": chain} if chain else {}
        return self._request("GET", "/v1/defi/tvl", params=params)

    def get_macro(self) -> Dict:
        """Macro market data (DXY, S&P, VIX, bonds). $0.02 x402."""
        return self._request("GET", "/v1/macro")

    def get_commodities_detail(self) -> Dict:
        """Detailed commodity analysis. $0.02 x402."""
        return self._request("GET", "/v1/commodities", params={"detailed": "true"})

    # ==================== AI INFERENCE ====================

    def inference(self, messages: List[Dict], model: str = "gpt-5.4-mini") -> Dict:
        """AI inference (OpenAI-compatible). $0.03 x402."""
        return self._request("POST", "/v1/inference", json_body={"messages": messages, "model": model})

    def complete(self, prompt: str, model: str = "gpt-5.4-mini") -> Dict:
        """Quick text completion. $0.03 x402."""
        return self._request("POST", "/v1/complete", json_body={"prompt": prompt, "model": model})

    # ==================== DISPUTE RESOLUTION ====================

    def resolve_dispute(self, policy: str, dispute: Dict[str, Any]) -> Dict:
        """AI-powered dispute resolution. $0.05 x402."""
        return self._request("POST", "/v1/disputes", json_body={"policy": policy, "dispute": dispute})

    # ==================== ASYNC SUPPORT ====================

    async def aget_prices(self, symbols: Optional[str] = None) -> Dict:
        params = {"symbols": symbols} if symbols else {}
        return await self._arequest("GET", "/v1/prices", params=params)

    async def aget_indicators(self, symbol: str, interval: str = "1d") -> Dict:
        return await self._arequest("GET", "/v1/indicators", params={"symbol": symbol, "interval": interval})

    async def aget_portfolio_intelligence(self, symbol: str) -> Dict:
        return await self._arequest("GET", "/v1/portfolio", params={"symbol": symbol})

    async def aget_market_pulse(self) -> Dict:
        return await self._arequest("GET", "/v1/market-pulse")

    async def aget_research(self, query: str) -> Dict:
        return await self._arequest("GET", "/v1/research", params={"query": query})

    async def aclose(self):
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None

    def close(self):
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
