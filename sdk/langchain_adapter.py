"""
Framework Adapters for AgentServices.
Drop-in tool objects for LangChain, CrewAI, and OpenAI function calling.

Usage:
  # LangChain
  from agentservices.langchain_adapter import AgentServicesToolkit
  toolkit = AgentServicesToolkit(base_url="https://api.agentservices.to")
  tools = toolkit.get_tools()
  agent = create_react_agent(llm, tools)

  # CrewAI
  from agentservices.crewai_adapter import AgentServicesTools
  tools = AgentServicesTools().get_tools()

  # OpenAI function calling
  from agentservices.openai_adapter import get_openai_tools
  tools = get_openai_tools()
"""

# ============================================================
# LangChain Adapter
# ============================================================

try:
    from langchain.tools import BaseTool
    from langchain.pydantic_v1 import BaseModel, Field
    from typing import Optional, Type
    import requests

    class AgentServicesBaseTool(BaseTool):
        """Base tool for AgentServices API."""
        base_url: str = "https://api.agentservices.to"
        name: str = "agentservices"
        description: str = "AgentServices API"

        def _make_request(self, method: str, path: str, **kwargs):
            url = f"{self.base_url}{path}"
            resp = requests.request(method, url, timeout=30, **kwargs)
            if resp.status_code == 402:
                return {"error": "Payment required (x402)", "needs_payment": True}
            return resp.json()

    class CryptoPriceTool(AgentServicesBaseTool):
        name: str = "get_crypto_price"
        description: str = "Get current crypto price (FREE). Input: symbol like BTC, ETH, SOL"

        def _run(self, symbol: str) -> str:
            data = self._make_request("GET", f"/v1/price/{symbol}")
            price = data.get("price_usd", data.get("data", {}).get("price_usd", "?"))
            return f"{symbol}: ${price}"

    class StockQuoteTool(AgentServicesBaseTool):
        name: str = "get_stock_quote"
        description: str = "Get real-time stock quote ($0.02 x402). Input: ticker like AAPL, TSLA"

        def _run(self, ticker: str) -> str:
            data = self._make_request("GET", f"/v1/stocks/{ticker}")
            if "error" in data:
                return f"Payment required for {ticker} quote"
            return f"{ticker}: ${data.get('price', '?')} ({data.get('change_pct', '?')}%)"

    class InferenceTool(AgentServicesBaseTool):
        name: str = "llm_inference"
        description: str = "LLM inference via GPT-5.4 ($0.03 x402). Input: prompt text"

        def _run(self, prompt: str) -> str:
            data = self._make_request("POST", "/v1/complete", params={"prompt": prompt, "model": "gpt-5.4-mini", "max_tokens": 500})
            if "error" in data:
                return "Payment required for inference"
            choices = data.get("choices", [])
            return choices[0]["message"]["content"] if choices else "No response"

    class TokenRiskTool(AgentServicesBaseTool):
        name: str = "token_risk_score"
        description: str = "Get risk score for a crypto token ($0.03 x402). Input: CoinGecko ID like 'bitcoin'"

        def _run(self, token: str) -> str:
            data = self._make_request("GET", f"/v1/token-risk/{token}")
            if "error" in data:
                return f"Payment required for {token} risk"
            return f"{token}: Risk {data.get('risk_score', '?')}/100 ({data.get('risk_label', '?')})"

    class CryptoSignalTool(AgentServicesBaseTool):
        name: str = "crypto_signal"
        description: str = "Get buy/sell signal for crypto ($0.04 x402). Input: symbol like BTC, ETH"

        def _run(self, symbol: str) -> str:
            data = self._make_request("GET", f"/v1/signals/{symbol}")
            if "error" in data:
                return f"Payment required for {symbol} signal"
            return f"{symbol}: {data.get('action', '?')} ({data.get('confidence', '?')} confidence, score {data.get('signal_score', '?')})"

    class WebExtractTool(AgentServicesBaseTool):
        name: str = "extract_web_content"
        description: str = "Extract clean text from any URL ($0.002 x402). Input: full URL"

        def _run(self, url: str) -> str:
            data = self._make_request("GET", "/v1/extract", params={"url": url})
            if "error" in data:
                return "Payment required for extraction"
            content = data.get("content", "")[:2000]
            return f"Title: {data.get('title', '?')}\n\n{content}"

    class AgentServicesToolkit:
        """Toolkit containing all AgentServices tools for LangChain."""

        def __init__(self, base_url: str = "https://api.agentservices.to"):
            self.base_url = base_url

        def get_tools(self):
            """Return all available tools."""
            tools = []
            for ToolClass in [CryptoPriceTool, StockQuoteTool, InferenceTool, TokenRiskTool, CryptoSignalTool, WebExtractTool]:
                tool = ToolClass()
                tool.base_url = self.base_url
                tools.append(tool)
            return tools

except ImportError:
    AgentServicesToolkit = None


# ============================================================
# CrewAI Adapter
# ============================================================

try:
    from crewai.tools import BaseTool as CrewAITool

    class CrewAICryptoPriceTool(CrewAITool):
        name: str = "get_crypto_price"
        description: str = "Get current crypto price. Input: symbol like BTC, ETH"

        def _run(self, symbol: str) -> str:
            import requests
            resp = requests.get(f"https://api.agentservices.to/v1/price/{symbol}", timeout=10)
            data = resp.json()
            price = data.get("price_usd", data.get("data", {}).get("price_usd", "?"))
            return f"{symbol}: ${price}"

    class CrewAIStockTool(CrewAITool):
        name: str = "get_stock_quote"
        description: str = "Get real-time stock quote. Input: ticker like AAPL, TSLA"

        def _run(self, ticker: str) -> str:
            import requests
            resp = requests.get(f"https://api.agentservices.to/v1/stocks/{ticker}", timeout=10)
            if resp.status_code == 402:
                return "Payment required (x402)"
            data = resp.json()
            return f"{ticker}: ${data.get('price', '?')} ({data.get('change_pct', '?')}%)"

    class CrewAIInferenceTool(CrewAITool):
        name: str = "llm_inference"
        description: str = "Run LLM inference via GPT-5.4. Input: prompt text"

        def _run(self, prompt: str) -> str:
            import requests
            resp = requests.post(f"https://api.agentservices.to/v1/complete", params={"prompt": prompt, "model": "gpt-5.4-mini"}, timeout=30)
            if resp.status_code == 402:
                return "Payment required (x402)"
            data = resp.json()
            choices = data.get("choices", [])
            return choices[0]["message"]["content"] if choices else "No response"

    class AgentServicesCrewAITools:
        """All AgentServices tools for CrewAI."""

        def get_tools(self):
            return [CrewAICryptoPriceTool(), CrewAIStockTool(), CrewAIInferenceTool()]

except ImportError:
    AgentServicesCrewAITools = None


# ============================================================
# OpenAI Function Calling Adapter
# ============================================================

def get_openai_tools():
    """Return OpenAI function-calling tool definitions for AgentServices."""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_crypto_price",
                "description": "Get current crypto price (FREE)",
                "parameters": {
                    "type": "object",
                    "properties": {"symbol": {"type": "string", "description": "Crypto symbol (BTC, ETH, SOL)"}},
                    "required": ["symbol"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_stock_quote",
                "description": "Get real-time stock quote ($0.02 via x402)",
                "parameters": {
                    "type": "object",
                    "properties": {"ticker": {"type": "string", "description": "Stock ticker (AAPL, TSLA)"}},
                    "required": ["ticker"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "llm_inference",
                "description": "Run LLM inference via GPT-5.4 ($0.03 via x402)",
                "parameters": {
                    "type": "object",
                    "properties": {"prompt": {"type": "string", "description": "Text prompt"}},
                    "required": ["prompt"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_token_risk",
                "description": "Get risk score for crypto token ($0.03 via x402)",
                "parameters": {
                    "type": "object",
                    "properties": {"token": {"type": "string", "description": "CoinGecko ID (bitcoin, ethereum)"}},
                    "required": ["token"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_crypto_signal",
                "description": "Get buy/sell signal for crypto ($0.04 via x402)",
                "parameters": {
                    "type": "object",
                    "properties": {"symbol": {"type": "string", "description": "Symbol (BTC, ETH)"}},
                    "required": ["symbol"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "extract_web_content",
                "description": "Extract clean text from URL ($0.002 via x402)",
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string", "description": "URL to extract"}},
                    "required": ["url"]
                }
            }
        },
    ]
