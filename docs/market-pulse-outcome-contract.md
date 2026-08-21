# Market Pulse — Outcome Contract

## Buyer outcome

```text
GET https://api.agentservices.to/v1/market-pulse
```

AgentServices returns a best-effort crypto market snapshot that bundles sentiment, trending activity, news, social activity, whale activity, and global-market modules. The endpoint is paid per request through x402. Use the returned `402 Payment Required` challenge as the authority for the exact Base/USDC price and settlement instructions.

The advertised price at publication is $0.05 USDC, but a payment challenge—not this document—is the authoritative price for a specific request.

## Successful paid-result envelope

```json
{
  "research_type": "market_pulse",
  "modules": {
    "sentiment": {
      "fear_greed_value": 0,
      "fear_greed_label": "<upstream label>",
      "interpretation": "<derived text>"
    },
    "trending": "<provider-dependent object>",
    "news": "<provider-dependent object>",
    "social": "<provider-dependent object>",
    "whale_activity": "<provider-dependent object>",
    "global_market": "<provider-dependent object>"
  },
  "errors": ["<module: truncated failure message>"],
  "timestamp": "<ISO-8601 UTC>",
  "synthesis": {
    "market_direction": "<derived text>",
    "sentiment_score": 0,
    "data_modules_active": 0,
    "modules_available": ["<successful module names>"]
  },
  "pricing_advantage": "<informational text>"
}
```

This is an illustrative schema with placeholders, not a current market result. `modules` is best-effort: a successful response can contain fewer than six modules, and unavailable modules are recorded in `errors`. Nested module-object fields may vary by provider; treat the top-level envelope, `modules.sentiment`, and `synthesis` as the stable integration surface.

## Sources and synthesis

| Module | Source or implementation |
|---|---|
| `sentiment` | Latest Fear & Greed datapoint from `alternative.me/fng` |
| `trending` | AgentServices DEX trending-token provider |
| `news` | AgentServices crypto-news provider, limited to five items |
| `social` | AgentServices social-trending provider |
| `whale_activity` | AgentServices on-chain whale-activity provider |
| `global_market` | AgentServices global-market provider |

`market_direction` is currently derived **only** from the Fear & Greed value. It does not aggregate or predict from the other modules. The thresholds are: below 25 bearish; 25–44 slightly bearish; 45–54 neutral; 55–74 bullish; 75 or higher very bullish. `sentiment_score` is the same Fear & Greed value.

## Limits

- This is a point-in-time data synthesis, not financial advice or a trading recommendation.
- Inspect `errors`, `data_modules_active`, and `modules_available` before relying on the report; upstream modules can fail independently.
- The API currently exposes `depth` and `currency` in its OpenAPI surface, but they do not change the current handler output. Do not rely on them as filters.
- The Fear & Greed interpretation is a simple thresholded signal, not a forecast.

## Buyer-retained payment receipt

Keep the original payment challenge and the buyer-side authorization or transaction evidence with a successful paid response:

```json
{
  "resource": "https://api.agentservices.to/v1/market-pulse",
  "x402_scheme": "exact",
  "network": "eip155:8453",
  "asset": "<USDC contract from the payment challenge>",
  "max_amount_required": "<atomic units from the payment challenge>",
  "pay_to": "<recipient from the payment challenge>",
  "payment_proof": "<buyer-retained x402 authorization or transaction evidence>",
  "received_at": "<ISO-8601 UTC>"
}
```

A `402` challenge establishes the requested purchase terms; it is not proof of settlement. Consider the report purchased only after the paid retry succeeds.
