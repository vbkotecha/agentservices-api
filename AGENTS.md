# Agent instructions — AgentServices API

Locked conventions for cloud agents and autonomous contributors. Follow on every trade-related change.

## WAR TIME trade API

**Path model:** venue-namespaced doors first.

| Phase | Path | Status |
|-------|------|--------|
| **Now** | `/v1/trade/hyperliquid/...` | Shipped |
| **Next** | `/v1/trade/{venue}/...` | Add venues under this prefix |
| **Later** | `/v1/trade/execute` | Venue-neutral router (not built yet) |
| **Never** | `/v1/trade/router` | Do not create or alias |

### Hyperliquid (first venue)

Base: `/v1/trade/hyperliquid`

| Endpoint | Method | Notes |
|----------|--------|-------|
| `/order` | POST | Forward agent-signed order |
| `/cancel` | POST | Forward agent-signed cancel |
| `/order` | GET | Status (query: `user`, `oid`) |
| `/order/{id}` | GET | Status by path param |
| `/policy` | GET / PUT | Execution leash |
| `/paper/order` | POST | Paper training |
| `/eval/order` | POST | Policy pass/fail eval |
| `/bootstrap` | GET | approveAgent signing docs |

**Request body:** include `market_type` — `spot`, `perp`, or `future` (validated). Hyperliquid implements perp + spot today; unsupported types return machine-readable `market_type_not_supported` (422).

**MCP tools:** `trade_hyperliquid_*` (primary). Legacy `hl_*` names are aliases only.

### Trade invariants (all venues)

- **Free policy leash** — max notional, coin allowlist, kill switch. No x402 on execution paths.
- **No venue key custody** — agents sign locally (`approveAgent` + local agent wallet). AgentServices never collects venue API keys or user private keys.
- **Door + forward** — policy check then forward signed payload. Not a smarter router; not a better fill.

### Dual trade door — execution vs monetization

Two doors, one product. Do not collapse them.

| Door | What | Monetization |
|------|------|--------------|
| **Execution** | `/v1/trade/{venue}/...` (HL today), later `/v1/trade/execute` | **Always free of x402 paywall.** Policy leash only. |
| **Data / discovery** | prices, indicators, search, synthesis, MCP paid tools | **x402** per-request SKUs (unchanged). |

**Locked:** venue execution paths (`/v1/trade/hyperliquid/order`, cancel, policy, paper, eval) must never return HTTP 402 or require USDC to pass policy and forward.

**Future multi-venue / `/v1/trade/execute`:** monetize via a small take on routed notional (~5 bps), embedded in the route — **not** by gating the HL door or blocking execution behind x402. Venue doors stay free; the router earns on flow, not on access.

### Competitive context

**HyprEarn** is a direct agentic multi-DEX rival. AgentServices trade doors are venue policy leashes, not a HyprEarn clone. Do not conflate the two products in docs or positioning.

## Agent operating rules

Cloud agents own the full ship loop end-to-end.

**Prefer committing and pushing straight to `main`.** Internal branches are OK only when the agent auto-merges to `main` before any user-facing update is considered done. **Never surface PR links to Vivek.** **Never leave an open PR waiting on him.**

### Ship workflow

1. **Implement** — commit directly on `main`, or use a short-lived internal branch.
2. **Test** — run relevant pytest / build; add tests for new trade paths and policy behavior.
3. **Land on `main`** — push to `main` directly, or squash-merge the branch yourself in the same session. No handoff.
4. **Deploy** — production auto-deploys on `main` push (Vercel, Yappa Ventures / `agentservices-api`).
5. **E2E smoke** after deploy:
   - `GET https://api.agentservices.to/health` — `deploy.commit` matches merge SHA
   - `GET https://api.agentservices.to/openapi.json` — trade paths present (e.g. `/v1/trade/hyperliquid/order`)
   - Probe stubs return expected responses (policy 403, validation 422) — **not 404**

### PRs (internal only)

PRs may exist for CI or audit trail, but they are **agent-owned**:

- Auto-merge to `main` before ending the turn — never leave one open for Vivek.
- Do not mention PR links in reports, summaries, or follow-ups.

### When to ping Vivek

Only for **human gates** that agents cannot satisfy:

- Wallet approvals, on-chain `approveAgent`, funded test wallets
- DNS, domain, or Vercel project ownership changes
- Secrets that are not in the environment (new API keys, OAuth client setup)

Never ask Vivek to review code, click merge, or approve deploys.

## Production

- **API:** `https://api.agentservices.to`
- **Health:** `GET /health`
- **OpenAPI:** `GET /openapi.json`
- **Deploy trigger:** push to `main`
