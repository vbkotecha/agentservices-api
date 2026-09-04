# Yappa Ops Dashboard

Founder-ops mission control for Yappa Ventures squads. Read-only Kanban board, squad status strip, and activity feed — styled like MissionControlHQ / squad.so.

Data lives in `public/board.json` so Main Bot (or any automation) can update the board without touching UI code.

## Quick start

```bash
cd ops-dashboard
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Deploy to Vercel

This is a standalone Next.js app — deploy it as its **own Vercel project** under Yappa Ventures (separate from the agentservices API).

### Option A: Vercel CLI

```bash
cd ops-dashboard
npm install -g vercel   # if needed
vercel                  # first deploy — follow prompts, set root to ops-dashboard
vercel --prod           # production deploy
```

When prompted:
- **Root directory:** `ops-dashboard` (if deploying from the monorepo root, set this in project settings)
- **Framework:** Next.js (auto-detected)

### Option B: Vercel Dashboard

1. Go to [vercel.com/new](https://vercel.com/new) and import the agentservices repo.
2. Set **Root Directory** to `ops-dashboard`.
3. Deploy — no env vars required for v1.

### Custom domain (optional)

In the Vercel project → **Settings → Domains**, add e.g. `ops.agentservices.to`:

```
ops.agentservices.to  →  CNAME  →  cname.vercel-dns.com
```

Or use the default `*.vercel.app` URL.

## Updating the board

Edit `public/board.json` and redeploy (or commit + push if connected to Git).

Schema:

| Section | Purpose |
|---------|---------|
| `meta` | Title, last-updated timestamp, updater name |
| `health` | Prod health check (status, HTTP code, version) |
| `squads` | Squad strip cards (Main Bot, Distribution, Radar, Money Maker) |
| `kanban.backlog` | Backlog column cards |
| `kanban.inFlight` | In-flight column cards |
| `kanban.done` | Done column cards |
| `activity` | Chronological activity feed |

Main Bot can update this file directly via PR or API hook in a future version.

## Stack

- Next.js 15 (App Router)
- TypeScript
- Tailwind CSS
- Static `board.json` (no database, no auth in v1)

## License

Same as parent repo.
