# AgentServices Buyer Quickstart

AgentServices gives AI agents paid access to research, market intelligence, on-chain data, and inference without API-key provisioning or a subscription. Requests settle per call in USDC on Base through [x402](https://x402.org).

## 1. Test the free surface

```bash
curl "https://api.agentservices.to/v1/prices?symbols=BTC,ETH"
```

## 2. Pick an outcome

Use a bundled endpoint when the agent needs a result, not raw plumbing:

| Outcome | Endpoint | Price* |
|---|---|---:|
| Deep research brief | `GET /v1/research?q=...` | $0.05 |
| Market pulse | `GET /v1/market-pulse` | $0.05 |
| Token risk report | `GET /v1/token-risk/{symbol}` | $0.03 |
| Portfolio intelligence | `GET /v1/portfolio?symbol=BTC` | $0.10 |
| On-chain overview | `GET /v1/onchain-overview` | $0.15 |
| Agent inference | `POST /v1/inference` | $0.03 |

`*` Indicative prices shown in the live catalog; the HTTP 402 response is authoritative for the requested call.

## 3. Let x402 handle payment

A paid request follows one simple loop:

1. Request the endpoint.
2. Receive `402 Payment Required` with the payment requirements.
3. Pay the stated amount in USDC on Base.
4. Retry with the x402 payment proof.
5. Receive the result.

There is no AgentServices API key to rotate. Keep wallet credentials in your agent runtime, never in source code or prompts.

## 4. Connect an agent directly

For MCP-compatible clients, add the hosted Streamable HTTP server:

```json
{
  "mcpServers": {
    "agentservices": {
      "url": "https://agentservices.to/mcp",
      "transport": "streamable-http"
    }
  }
}
```

For direct integrations, use the [OpenAPI docs](https://api.agentservices.to/docs) or the [JavaScript SDK](https://www.npmjs.com/package/@agentservices/client).

## 5. Verify hosted MCP discovery

Verify the hosted Streamable HTTP MCP server and its live tool catalog without an API key, wallet, or paid call:

```bash
python3 examples/mcp_discovery_buyer_proof.py
```

It verifies the server protocol and confirms free tools including `crypto_prices`, `fear_greed`, and `agent_context` from the live MCP catalog.

## 6. Prove one complete free SDK call

Run the JavaScript SDK against the live free price route—without a wallet, API key, or paid call:

```bash
node examples/sdk_free_price_buyer_proof.js BTC ETH
```

This proves the published SDK buyer path can retrieve an actual result before a buyer configures x402 spend.

## 7. Run a no-spend x402 buyer proof

Verify a real free response and decode the live x402 requirements for a paid token-risk report—without signing or settling any payment:

```bash
python3 examples/token_risk_buyer_proof.py BTC
```

The script uses the canonical `api.agentservices.to` domain, confirms the free price surface, then verifies and displays the exact Base/USDC payment challenge for `GET /v1/token-risk/BTC`. Read the [Token Risk Outcome Contract](token-risk-outcome-contract.md) for the paid result schema, method, provenance, limits, and buyer-retained receipt guidance.

## 8. Verify the paid JavaScript SDK path without spending

The SDK surfaces x402 payment challenges as structured errors. Verify the paid technical-indicator route and decode its live Base/USDC requirements without signing or settling a payment:

```bash
node examples/sdk_paid_indicator_buyer_proof.js BTC
```

The proof must receive HTTP 402, show the declared amount/network/recipient, and stop before payment. A real buyer then pays with an x402-compatible wallet and retries the request.

## 9. Understand the market-pulse outcome

For a documented snapshot contract—including partial-module behavior, source boundaries, synthesis limits, and x402 receipt guidance—read the [Market Pulse Outcome Contract](market-pulse-outcome-contract.md).

## 10. Understand the research-brief outcome

For a paid, source-auditable web-research brief, read the [Research Brief Outcome Contract](research-brief-outcome-contract.md). It documents source/extraction status, keyword-synthesis limits, no-result behavior, and buyer-retained x402 evidence.

## 11. Build a buyer-retained receipt

After a successful paid retry, turn the original `payment-required` value, returned response body, and wallet transaction or authorization reference into a portable procurement receipt:

```bash
python3 examples/build_x402_receipt.py \\
  --payment-required-file payment-required.txt \\
  --result-file paid-result.json \\
  --payment-proof '<transaction hash or authorization reference>'
```

The builder does not sign or settle payments. It records quoted terms and hashes the buyer-held challenge and result for later verification.

## 12. Start with one paid call

```text
Goal: produce a concise research brief on the Base ecosystem.
Call: GET https://api.agentservices.to/v1/research?q=Base ecosystem
Budget: $0.05 USDC on Base
Output: synthesized research returned to the agent after payment.
```

## Links

- [Live API](https://agentservices.to)
- [OpenAPI docs](https://api.agentservices.to/docs)
- [MCP endpoint](https://agentservices.to/mcp)
- [x402 discovery](https://agentservices.to/.well-known/x402)
- [Source and SDK](https://github.com/vbkotecha/agentservices-api)
