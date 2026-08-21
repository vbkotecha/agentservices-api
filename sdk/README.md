# AgentServices Client SDK

Client SDK for [AgentServices](https://agentservices.to) — paid data APIs for AI agents.

## Install

```bash
npm install @agentservices/client
```

For the complete buyer path from discovery through a buyer-retained receipt, follow [`docs/buyer-quickstart.md`](../docs/buyer-quickstart.md). The exact next action is to run `node examples/sdk_free_price_buyer_proof.js BTC ETH` from the repository root.

## Quick Start

```javascript
const { AgentServicesClient } = require("@agentservices/client");

const client = new AgentServicesClient();

// Free endpoints — no payment needed
const btc = await client.getPrice("BTC");
const batch = await client.getPrices(["BTC", "ETH", "SOL"]);
const fearGreed = await client.getFearGreed();
const geo = await client.getGeo("8.8.8.8");
const policies = await client.listPolicies();

// Paid endpoints — require x402 payment (USDC on Base)
// These return 402 Payment Required without payment proof
const indicators = await client.getIndicators("BTC");     // $0.02
const yields = await client.getYields({ limit: 20 });      // $0.02
const metadata = await client.getMetadata("https://example.com"); // $0.01
const ruling = await client.fileDispute({                  // $0.05
  policy: "freelance-delivery",
  claimant: "0x123...",
  respondent: "0x456...",
  claim: "Service delivered but payment refused",
  desiredRemedy: "Full payment of 0.5 ETH",
  evidence: [],
});
```

## Endpoints

| Endpoint | Method | Price | Description |
|---|---|---|---|
| `/v1/price/{symbol}` | GET | FREE | Current crypto price |
| `/v1/prices?symbols=` | GET | FREE | Batch crypto prices |
| `/v1/fear-greed` | GET | FREE | Crypto Fear & Greed Index |
| `/v1/geo/{ip}` | GET | FREE | IP geolocation |
| `/v1/policies` | GET | FREE | List dispute policy templates |
| `/v1/indicators/{symbol}` | GET | $0.02 | RSI, Bollinger Bands, ATR, Support/Resistance; returns x402 402 before payment |
| `/v1/yields` | GET | $0.02 | Top DeFi yield pools by TVL |
| `/v1/metadata?url=` | GET | $0.01 | URL metadata extraction |
| `/v1/disputes` | POST | $0.05 | Policy-driven dispute resolution (AgentCourt engine) |

## Dispute Resolution

File disputes using 7 policy templates:

- **freelance-delivery** — Work-for-hire delivery disputes
- **milestone-payment** — Milestone-based payment disputes
- **bug-bounty** — Severity, reproducibility, disclosure disputes
- **api-quality** — API quality issues on paid calls
- **scope-dispute** — Agent mandate/scope violations
- **sla-monitoring** — SLA violation disputes
- **physical-commerce** — Physical product disputes

## x402 Payment

Paid endpoints use the [x402 protocol](https://x402.org) with USDC on Base Mainnet. A request without proof returns HTTP 402 with the authoritative terms for that call; the SDK exposes this challenge rather than pretending it has paid.

Buyer sequence:

1. Call a free method to verify connectivity.
2. Call one paid method and inspect its structured 402 challenge.
3. Pay the returned terms with an x402-compatible wallet, then retry.
4. Retain the successful response and payment reference; the repository receipt builder can hash both for portable evidence.

The challenge is price discovery, not proof of settlement. The SDK and its no-spend examples do not claim adoption, settlement, or revenue.

To enable automatic payment, pass wallet credentials:

```javascript
const client = new AgentServicesClient({
  walletAddress: "0x...",
  privateKey: "0x...",
});
```

## License

MIT
