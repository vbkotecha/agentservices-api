"""
AIServices API Client
======================
Minimal sync client for all AIServices x402 endpoints.
"""
import json
import httpx
from typing import Optional, Dict, Any, List

BASE_URL = "https://agentservices.to"

class AIServicesClient:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url.rstrip("/")
    
    def get_prices(self, symbols: Optional[str] = None) -> Dict:
        """Get crypto prices (FREE). e.g., 'BTC,ETH,XRP'"""
        params = {"symbols": symbols} if symbols else {}
        r = httpx.get(f"{self.base_url}/v1/prices", params=params, timeout=15)
        return r.json()
    
    def get_indicators(self, symbol: str, interval: str = "1d") -> Dict:
        """Get technical indicators — RSI, MACD ($0.02 x402)"""
        r = httpx.get(f"{self.base_url}/v1/indicators", params={"symbol": symbol, "interval": interval}, timeout=15)
        return r.json()
    
    def get_defi_yields(self, chain: Optional[str] = None) -> Dict:
        """Get DeFi yields ($0.02 x402)"""
        params = {"chain": chain} if chain else {}
        r = httpx.get(f"{self.base_url}/v1/defi/yields", params=params, timeout=15)
        return r.json()
    
    def get_fear_greed(self) -> Dict:
        """Get Fear & Greed index (FREE)"""
        r = httpx.get(f"{self.base_url}/v1/fear-greed", timeout=10)
        return r.json()
    
    def get_geo(self, ip: Optional[str] = None) -> Dict:
        """Get IP geolocation (FREE)"""
        params = {"ip": ip} if ip else {}
        r = httpx.get(f"{self.base_url}/v1/geo", params=params, timeout=10)
        return r.json()
    
    def get_url_metadata(self, url: str) -> Dict:
        """Extract metadata from URL ($0.01 x402)"""
        r = httpx.get(f"{self.base_url}/v1/metadata", params={"url": url}, timeout=20)
        return r.json()
    
    def resolve_dispute(self, policy: str, dispute: Dict[str, Any]) -> Dict:
        """AI-powered dispute resolution ($0.05 x402)"""
        r = httpx.post(f"{self.base_url}/v1/disputes", json={"policy": policy, "dispute": dispute}, timeout=30)
        return r.json()
    
    def list_policies(self) -> List[Dict]:
        """List dispute resolution policies (FREE)"""
        r = httpx.get(f"{self.base_url}/v1/policies", timeout=10)
        return r.json()
