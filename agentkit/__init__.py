"""
AgentServices Action Provider for Coinbase AgentKit.

Provides AI agents with access to AgentServices' 50+ data APIs via x402 payments.
Agents can query crypto prices, market indicators, DeFi yields, onchain analytics,
portfolio intelligence, web search, AI inference, and more.
"""

from .agentservices_action_provider import agentservices_action_provider

__all__ = ["agentservices_action_provider"]
