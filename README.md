# EV Sports Platform

A **decision-support** tool that surfaces a daily, ranked dashboard of positive-expected-value (+EV) bets across sports. It **never places bets** — it recommends, and a human acts.

> Read [`research/viability-analysis.md`](research/viability-analysis.md) and [`research/tech-stack.md`](research/tech-stack.md) first. The whole product hinges on one gate: **can a model beat the de-vigged closing line (positive CLV)?** Everything here is structured around proving that per sport before trusting it.

## Architecture (monorepo)

```
.
├── worker/        Python: ingestion + modeling + devig/EV/CLV. Runs on a schedule.
├── web/           Next.js (React + TS) dashboard. Reads results from Supabase.
├── supabase/      SQL migrations (schema is source-of-truth in git).
└── research/      Analysis & design docs.
```

**Data flow:** `worker` pulls odds + stats → runs per-sport models → computes **no-vig fair prob → EV → Kelly → CLV** → writes ranked `ev_bets` to Supabase Postgres → `web` reads them (RLS-protected) and renders the sorted, filterable table with a SHAP rationale per bet.

The heart of the system is [`worker/core/devig.py`](worker/core/devig.py) and [`worker/core/clv.py`](worker/core/clv.py) — the EV and closing-line-value math. A perfect model with the wrong EV baseline loses money; this is where correctness matters most.

## Quick start

```bash
# 1. Secrets — copy and fill (never commit .env)
cp .env.example .env

# 2. Python worker
cd worker
python -m venv .venv && . .venv/Scripts/activate    # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m worker.run --sport golf --dry-run          # prints ranked +EV table, writes nothing

# 3. Database schema (requires Supabase project + CLI)
cd ../supabase
supabase db push

# 4. Web dashboard
cd ../web
pnpm install
pnpm dev
```

## Security

- All credentials come from `.env` (git-ignored). The `SUPABASE_SERVICE_ROLE_KEY` is **server-side only** — never in the web bundle.
- If any API key was ever pasted into a chat, doc, or commit, **rotate it**.
- Supabase MCP (if used with Claude Code) must point at a **dev** project, never production data.

## Status

Foundation scaffold. `golf` is the first vertical (the CLV gate). Other sports plug into the same `SportModel` interface. See each package's README for what's real vs. stubbed.
