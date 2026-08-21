# Token Risk Report — Outcome Contract

## Buyer outcome

```text
GET https://api.agentservices.to/v1/token-risk/{token}
```

AgentServices returns a compact, machine-readable token risk assessment from a market snapshot. It is paid per request through x402; the `402 Payment Required` challenge is authoritative for the exact Base/USDC amount and settlement instructions.

The no-spend buyer proof verifies the public purchase path without settling a payment:

```bash
python3 examples/token_risk_buyer_proof.py BTC
```

At the latest verification, the BTC request challenge required 30,000 Base-USDC atomic units ($0.03) on `eip155:8453`. That price is not a promise for future calls; buyers must use the payment challenge returned for their request.

## Input

| Field | Type | Meaning |
|---|---|---|
| `token` | path string | CoinGecko-compatible token identifier, such as `bitcoin` or `ethereum`. |

`BTC` is valid only where upstream identifier handling recognizes it; use a CoinGecko identifier for portable direct HTTP integrations.

## Successful paid-result shape

```json
{
  "token": "<requested token>",
  "risk_score": 0,
  "risk_label": "<Low|Moderate|High|Extreme>",
  "dimensions": {
    "volatility": 0.0,
    "market_cap_risk": 0,
    "liquidity_risk": 0.0
  },
  "market_data": {
    "price_usd": 0.0,
    "change_24h_pct": 0.0,
    "volume_24h_usd": 0.0,
    "market_cap_usd": 0.0
  },
  "momentum": "<bullish|bearish|neutral>",
  "recommendation": "<Stable|Monitor|Caution>",
  "timestamp": "<ISO-8601 UTC>"
}
```

This is a schema illustration with placeholders, **not** a current market report or a previously paid result.

## Method

The response is a deterministic synthesis of the upstream market snapshot:

- **Volatility risk (30%)**: absolute 24-hour price movement, capped at 100 after multiplication by 3.
- **Market-cap risk (40%)**: a banded score; lower market capitalization receives a higher risk value.
- **Liquidity risk (30%)**: inverse 24-hour-volume-to-market-cap proxy.
- **Momentum**: `bullish` above +2% 24-hour movement, `bearish` below -2%, otherwise `neutral`.
- **Composite score**: 0 is lower measured market risk; 100 is higher measured market risk.

Risk labels: `Low` below 30, `Moderate` below 55, `High` below 75, otherwise `Extreme`.

## Provenance and limits

The current implementation fetches the following fields from the CoinGecko Simple Price API: `usd`, `usd_24h_change`, `usd_24h_vol`, and `usd_market_cap`. The response's `timestamp` records AgentServices generation time.

The report is a snapshot-based market-risk signal. It does not assess smart-contract security, counterparty risk, holder concentration, regulatory status, or investment suitability. It is not financial advice. Unsupported identifiers and upstream failures return an error object such as:

```json
{ "status": "not_found", "error": "Token '<token>' not found" }
```

## Buyer-retained payment receipt

Retain the original x402 challenge and your own payment authorization or transaction evidence alongside a successful paid response:

```json
{
  "resource": "https://api.agentservices.to/v1/token-risk/<token>",
  "x402_scheme": "exact",
  "network": "eip155:8453",
  "asset": "<USDC contract from the payment challenge>",
  "max_amount_required": "<atomic units from the payment challenge>",
  "pay_to": "<recipient from the payment challenge>",
  "payment_proof": "<buyer-retained x402 authorization or transaction evidence>",
  "received_at": "<ISO-8601 UTC>"
}
```

A payment challenge is price discovery, not proof of settlement. Treat a request as purchased only after the paid retry returns a successful report.

## Programmatic receipt builder

Build a portable receipt from the buyer-held x402 challenge, payment reference, and successful response body:

```bash
python3 examples/build_x402_receipt.py \
  --payment-required-file payment-required.txt \
  --result-file paid-token-risk.json \
  --payment-proof '<wallet transaction hash or x402 authorization reference>'
```

The JSON output binds the quoted resource and payment terms to SHA-256 digests of the original challenge and result. It never signs a payment and does not claim settlement; verify settlement with the selected wallet or facilitator.
