# HackerNoon Proof of Usefulness Submission Kit — AgentServices

Prepared for the Proof of Usefulness hackathon submission. This document is a factual source sheet for the questionnaire, score report, and final HackerNoon article.

## Project

**Name:** AgentServices  
**Project URL:** https://agentservices.to  
**API documentation:** https://api.agentservices.to/docs  
**OpenAPI specification:** https://api.agentservices.to/openapi.json  
**MCP endpoint:** https://agentservices.to/mcp  
**Source code:** https://github.com/vbkotecha/agentservices-api  
**Buyer quickstart:** https://github.com/vbkotecha/agentservices-api/blob/main/docs/buyer-quickstart.md

## The problem

Software agents can call tools, but useful external data is still fragmented across APIs, authentication systems, pricing models, and payment rails. An agent that needs market, crypto, macroeconomic, exchange, or on-chain information should not require a human to create and rotate a separate credential for every provider.

## The solution

AgentServices exposes agent-ready research and market-data capabilities through one documented API and MCP surface. Requests can be settled per call with x402 on Base, so an agent can pay for a specific result instead of opening an account, storing a long-lived API key, or buying an unused subscription.

The product is designed around a simple buyer outcome: give an agent a reliable, structured answer it can use immediately, with payment and provenance handled at the protocol boundary.

## Who uses it

- Autonomous agents that need current market or on-chain data.
- Developers building research, trading, monitoring, and financial-analysis workflows.
- Teams that want a single integration surface for multiple paid data capabilities.

## Technical implementation

- HTTP API with a public OpenAPI document and server-rendered interactive docs.
- MCP surface for tool-capable agent clients.
- x402 payment negotiation and settlement on Base.
- Structured JSON responses intended for programmatic consumption.
- Public buyer quickstart and source repository for reproducible integration.

## Proof of usefulness

The service is live and externally testable:

1. Open the API docs and inspect the available operations: https://api.agentservices.to/docs
2. Fetch the OpenAPI contract: https://api.agentservices.to/openapi.json
3. Call the representative BTC indicator endpoint: https://api.agentservices.to/v1/indicators/BTC
4. The endpoint returns the x402 payment requirement rather than silently failing or requiring an undocumented credential.
5. A real self-pay on Base was subsequently completed and returned live BTC indicator data, demonstrating the complete request → payment → useful response path.

This submission does **not** claim fabricated user counts, revenue, or retention. The verifiable traction claim is narrower: the paid settlement path has been exercised end-to-end against a live service.

## Business model

AgentServices charges per successful outcome through x402. The initial model is usage-based micropayments; future packaging can add governed budgets, approved-provider routing, spend logs, receipts, and enterprise controls for teams operating many agents.

## Why this matters

AgentServices turns payment from an onboarding obstacle into part of the agent's tool call. That makes small, occasional, and machine-selected data purchases practical. The useful unit is not an API credential; it is a verified result an agent can obtain and pay for at the moment it needs it.

## Suggested final article framing

**Working title:** Agents Do Not Need More Tools. They Need a Way to Buy Useful Results.

**Opening:** The missing layer in agent infrastructure is not another demo tool. It is the ability to discover a useful external capability, pay for one call, and receive structured data without a human creating an account first.

**Body sections:**

1. The credential-and-subscription bottleneck.
2. A live API and MCP surface built for machine buyers.
3. x402 payment as an agent action, not a checkout page.
4. The BTC indicator flow as a reproducible proof.
5. What governed agent spend enables next.

**Closing:** Useful agents need access to the world outside their context window. AgentServices provides one path to that access: discoverable capabilities, machine-readable contracts, and payment that can happen at the point of use.

## Submission checklist

- [ ] Complete the Proof of Usefulness questionnaire.
- [ ] Generate and save the PoU score/report.
- [ ] Add the score/report evidence to the final article.
- [ ] Publish the HackerNoon article before the 2026-08-10 deadline.
- [ ] Preserve the live links above exactly; do not substitute legacy `aiservices.to` URLs.
