"""AIServices SDK (deprecated — import agentservices instead)."""
import warnings
warnings.warn(
    "The 'aiservices' package is deprecated. Use 'agentservices' instead.",
    DeprecationWarning,
    stacklevel=2,
)
# Re-export from new package for backwards compatibility
from agentservices.client import AgentServicesClient
from agentservices.langchain_tools import create_langchain_tools as create_aiservices_tools

__version__ = "5.3.0"
__all__ = ["AgentServicesClient", "create_aiservices_tools"]
