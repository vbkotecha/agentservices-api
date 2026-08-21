from setuptools import setup, find_packages

setup(
    name="agentservices",
    version="5.3.0",
    description="AgentServices SDK — 50 paid APIs for AI agents (crypto data, DeFi yields, market intelligence, on-chain analytics). Built-in x402 payments.",
    long_description="""AgentServices Python SDK
========================
50 paid APIs for AI agents with built-in x402 (USDC on Base) payments.

## Quick Start

```python
from agentservices import AgentServicesClient

client = AgentServicesClient()
prices = client.get_prices("BTC,ETH")  # FREE
report = client.get_portfolio_intelligence("BTC")  # $0.10 - full analysis
```

## LangChain Integration

```python
from agentservices import create_langchain_tools
from langchain.agents import create_react_agent

tools = create_langchain_tools()
agent = create_react_agent(llm, tools)
```

## CrewAI Integration

```python
from agentservices import create_crewai_tools
from crewai import Agent

tools = create_crewai_tools()
agent = Agent(role='Crypto Analyst', tools=tools, llm=llm)
```

## x402 Payments

Paid endpoints return a 402 response with payment details.
The SDK auto-detects this and returns structured payment info.

For auto-pay, provide a wallet private key:
```python
client = AgentServicesClient(wallet_private_key="0x...")
```

## Endpoints (50 total, 38 paid)

**Free:** crypto prices, fear-greed, IP geo, trending, gas, news, social, global market, swap quotes, predictions, dispute policies
**Paid ($0.01-$0.25):** indicators, DeFi yields, search, metadata, portfolio intelligence, DeFi strategy, market pulse, on-chain overview, deep research, AI inference, token risk, crypto signals, whale tracking, and more

Full API docs: https://agentservices.to/docs
""",
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=["httpx>=0.27", "pydantic>=2.0"],
    extras_require={
        "langchain": ["langchain>=0.1"],
        "crewai": ["crewai>=0.30"],
        "all": ["langchain>=0.1", "crewai>=0.30"],
    },
    python_requires=">=3.10",
    author="Vivek Kotecha",
    author_email="support@agentservices.to",
    url="https://agentservices.to",
    license="MIT",
    keywords=[
        "x402", "crypto", "ai-agents", "langchain", "crewai", "base", "usdc",
        "mcp", "defi", "market-intelligence", "onchain", "api", "agentservices"
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
