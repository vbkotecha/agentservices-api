# Research Brief — Outcome Contract

## Buyer outcome

```text
GET https://api.agentservices.to/v1/research?q=<research-question>&sources=3
```

AgentServices returns a machine-readable research brief from web search, attempted source extraction, and deterministic keyword-based synthesis. It is paid per request through x402. The returned `402 Payment Required` challenge is authoritative for the price, asset, and settlement instructions for that request.

This is a bounded research input, not a claim that every cited page was retrieved or that the brief independently verifies every source assertion.

## Input

| Field | Type | Default | Meaning |
|---|---|---:|---|
| `q` | query string | required | Research question or topic. |
| `sources` | integer | `3` | Requested number of search results to attempt to analyze. The implementation caps it at `5`. |

Use a specific question. Example: `Bitcoin ETF flows` rather than `Bitcoin`.

## Successful paid-result shape

```json
{
  "query": "<requested query>",
  "research_type": "deep_research",
  "sources_analyzed": 0,
  "sources_successfully_extracted": 0,
  "synthesis": {
    "brief": "<short source-attributed text>",
    "key_findings": ["<detected metric or fallback>"],
    "themes_detected": ["<detected theme or fallback>"],
    "sentiment": "<positive|negative|neutral>",
    "sentiment_drivers": {
      "positive_signals": 0,
      "negative_signals": 0
    }
  },
  "sources": [
    {
      "title": "<search result title>",
      "url": "<search result URL>",
      "snippet": "<search snippet>",
      "extraction_status": "<extracted|skipped|error: ...>",
      "content_preview": "<up to 500 extracted characters or empty string>"
    }
  ],
  "pricing_advantage": "<implementation message>",
  "timestamp": "<ISO-8601 UTC>"
}
```

The schema is illustrative. It is not a live research result, guarantee of source count, or settlement receipt.

## Method and provenance

1. The service searches for `sources + 2` results.
2. It selects at most the requested number of results (capped at five) and attempts extraction only for HTTP(S) URLs.
3. Each source returns an `extraction_status`; an extraction error is represented in that field and does not make the entire call fail.
4. The brief uses source text where available, otherwise the result snippet. `key_findings` detect dollar amounts and percentages. `themes_detected` and `sentiment` are keyword-based signals over returned source text.

`sentiment` is an implementation-level text signal, not a market prediction, source credibility score, or factual consensus. Source URLs and extraction statuses are the provenance needed to audit a brief before relying on it.

## Empty and partial outcomes

If search returns no results, the result is a successful structured no-result response:

```json
{
  "query": "<requested query>",
  "status": "no_results",
  "findings": [],
  "timestamp": "<ISO-8601 UTC>"
}
```

A source count below the request, zero successful extractions, or an extraction error means the returned synthesis has reduced evidence. Buyers should inspect `sources`, `sources_analyzed`, and `sources_successfully_extracted` before acting.

## Buyer-retained payment evidence

Retain the original x402 challenge, your own payment authorization or transaction evidence, and the paid response body. A challenge is price discovery, not proof of settlement. A paid retry that returns the response is evidence of fulfillment; settlement status remains a wallet/facilitator concern unless separately confirmed.
