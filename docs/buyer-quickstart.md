# AgentServices Buyer Quickstart

AgentServices gives AI agents paid access to research, market intelligence, on-chain data, and inference without API-key provisioning or a subscription. Paid requests use per-call x402 terms in USDC on Base; the request's payment challenge is authoritative.

## Canonical buyer path

Run this path in order. It moves from discovery to a free result, then a paid challenge, a paid outcome, and buyer-retained evidence. The no-spend proofs stop before signing; a `402` challenge is not proof of fulfillment, settlement, adoption, or revenue.

### 1. Discover the hosted service

From the repository root, run:

```bash
python3 examples/mcp_discovery_buyer_proof.py
```

This verifies the hosted Streamable HTTP MCP protocol and live tool catalog without an API key, wallet, or paid call. It proves discovery only; it does not invoke a paid tool or prove a paid result.

### 2. Get a free result

Run the published JavaScript SDK against the free price route:

```bash
node examples/sdk_free_price_buyer_proof.js BTC ETH
```

This proves the SDK buyer path can return an actual price result before an agent configures x402 spend. It does not exercise a paid endpoint.

### 3. Inspect the paid challenge

Run the paid SDK proof:

```bash
node examples/sdk_paid_indicator_buyer_proof.js BTC
```

It must receive HTTP `402`, decode the live Base/USDC requirements, and stop before signing or settling. The equivalent no-spend proof for a bundled outcome is:

```bash
python3 examples/token_risk_buyer_proof.py BTC
```

That script verifies a free response, then decodes the token-risk payment challenge without making a payment. Read the [Token Risk Outcome Contract](token-risk-outcome-contract.md) before relying on that snapshot-based signal.

### 4. Choose and fulfill one paid outcome

Start with one concrete buyer outcome. The research brief is the recommended first call:

```text
GET https://api.agentservices.to/v1/research?q=Base%20ecosystem&sources=3
```

The payment loop is:

1. Request the outcome endpoint.
2. Receive `402 Payment Required` and read its payment requirements.
3. Pay the stated amount in USDC on Base with an x402-compatible wallet.
4. Retry with the payment proof.
5. Retain the returned result and the original challenge.

The request's HTTP 402 challenge is authoritative for the amount, asset, recipient, and network. A successful paid retry demonstrates response fulfillment; settlement remains a wallet/facilitator concern and must be verified separately.

Available outcome contracts:

| Outcome | Endpoint | Contract and disclosed limit |
|---|---|---|
| Research brief | `GET /v1/research?q=...&sources=3` | [Research Brief](research-brief-outcome-contract.md): source/extraction status is explicit; synthesis is deterministic keyword analysis, not a market prediction or credibility score. |
| Token risk report | `GET /v1/token-risk/{token}` | [Token Risk](token-risk-outcome-contract.md): snapshot-based volatility, market-cap, and liquidity-proxy signal; no smart-contract, counterparty, holder-concentration, regulatory, or suitability analysis. |
| Market pulse | `GET /v1/market-pulse` | [Market Pulse](market-pulse-outcome-contract.md): best-effort modules; inspect `errors`, `data_modules_active`, and `modules_available`; direction is derived only from Fear & Greed. |

Indicative prices in these documents are not guarantees. Use the payment challenge returned for the specific request.

### 5. Build a buyer-retained receipt

After a paid retry returns a result, save the original challenge and result, then run:

```bash
python3 examples/build_x402_receipt.py \
  --payment-required-file payment-required.txt \
  --result-file paid-result.json \
  --payment-proof '<transaction hash or authorization reference>'
```

The builder binds the quoted resource and payment terms to SHA-256 digests of the buyer-held challenge and result. It does not sign, settle, or independently verify payment. Verify settlement with the selected wallet or facilitator.

**Exact next buyer action:** from the repository root, run `python3 examples/mcp_discovery_buyer_proof.py`. Then continue through steps 2–5 above.

## Direct integration

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

For direct integrations, use the [OpenAPI docs](https://api.agentservices.to/docs) or the [JavaScript SDK](https://www.npmjs.com/package/@agentservices/client). Free discovery and SDK calls require no AgentServices API key. Keep wallet credentials in the agent runtime, never in source code or prompts.

## Links

- [Live API](https://agentservices.to)
- [OpenAPI docs](https://api.agentservices.to/docs)
- [MCP endpoint](https://agentservices.to/mcp)
- [x402 discovery](https://agentservices.to/.well-known/x402)
- [Source and SDK](https://github.com/vbkotecha/agentservices-api)
