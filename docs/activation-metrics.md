# AgentServices Activation Metrics

## Definition

**Activation event:** a unique payer wallet address successfully settles at least one paid AgentServices request (HTTP 200 returned after a valid x402 payment proof for a previously-challenged 402 endpoint).

**Activation funnel:**

| Stage | Event | Measurement source |
|---|---|---|
| Discovery | First request to any AgentServices endpoint (free or paid) | API access logs (unique IP or user-agent) |
| Free use | Successful call to a free endpoint (e.g. `GET /v1/prices`) | API access logs (200 on free routes) |
| Payment challenge | First 402 response to a unique requester | API access logs (402 status on paid routes) |
| **Activation** | **First successful x402 settlement from a unique payer** | **x402 facilitator settlement confirmation + API 200 after payment proof** |
| Retention | Second paid call from the same payer within 7 days | Facilitator settlement logs (repeat payer addresses) |

## Current baseline (Aug 11, 2026)

- Self-pay settlement proved working (Jul 28, 2026: HTTP 200, real BTC indicator data returned after x402 payment).
- Zero external paid activations recorded. No external buyer has executed a paid request and retained the receipt.
- No analytics infrastructure exists on the API. Measurement is currently manual: facilitator dashboard + API access logs + receipt artifacts.

## Measurement limitations

1. **No server-side analytics:** the API does not currently log request counts, unique callers, or settlement events to a persistent store. Adding lightweight request logging middleware is the prerequisite for automated measurement.
2. **Facilitator-dependent:** settlement confirmation depends on the x402 facilitator (CDP/Dexter). If the facilitator does not expose per-payee settlement webhooks, activation must be verified manually from transaction history.
3. **IP-based deduplication is unreliable:** agents may share egress IPs or use rotating addresses. Payer wallet address is the only reliable unique identifier.
4. **Self-pay is not adoption:** settlement from the project's own wallet proves the payment rail works but does not constitute an external buyer activation.
5. **Receipt artifacts are buyer-held:** the receipt builder produces portable evidence but AgentServices does not retain or aggregate receipts server-side.

## What counts as activation

| Claim | Evidence required |
|---|---|
| "Payment rail works" | Self-pay with HTTP 200 and real data returned (achieved Jul 28) |
| "One external buyer paid" | Unique external wallet settled a paid request + API returned 200 + buyer retained receipt |
| "Repeat buyer" | Same external wallet settled 2+ paid requests across separate sessions |
| "Revenue" | Settlement verified on-chain + net of gas + facilitator fees |

## Next measurement infrastructure

The minimum viable analytics addition is a lightweight middleware that:
1. Counts requests per status code (200/402/4xx/5xx) per endpoint.
2. Extracts and deduplicates payer addresses from successful settlement responses.
3. Exposes a private `/v1/stats` endpoint for internal monitoring.

This is explicitly out of scope for AS-BUYER-003 but is the prerequisite for AS-BUYER-001 (first external paid integration verification).
