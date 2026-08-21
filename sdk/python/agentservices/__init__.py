"""
AgentServices SDK — Paid APIs for AI agents.
Data, search, market intelligence, and services agents pay for via x402.

Usage:
    from agentservices import AgentServicesClient
    client = AgentServicesClient()
    prices = client.get_prices("BTC,ETH")

LangChain:
    from agentservices import create_langchain_tools
    tools = create_langchain_tools()

CrewAI:
    from agentservices import create_crewai_tools
    tools = create_crewai_tools()
"""
from .client import AgentServicesClient
from .langchain_tools import create_langchain_tools

__version__ = "5.3.0"
__all__ = ["AgentServicesClient", "create_langchain_tools"]

# CrewAI support is optional (requires crewai package)
try:
    from .crewai_tools import create_crewai_tools
    __all__.append("create_crewai_tools")
except ImportError:
    pass
