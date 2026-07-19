# EV Sports Platform — Project Memory

<!-- Keep this file under ~200 lines. Facts here load every session; put deep detail in research/ and link it. -->

## 1. Project Identity
- **Name:** EV Sports Platform.
- **One-liner:** A web app that surfaces a daily, ranked, *explained* dashboard of positive-expected-value (+EV) sports bets. **Decision support only — it never places bets.**
- **Core mission:** Show only bets where the math genuinely beats the market, and prove it with Closing Line Value (CLV).
- **Success criteria (north star):** **positive aggregate CLV** of tracked bets. A sport isn't shown as real ("trusted") until it clears the CLV gate. Growth without positive CLV = failure.
- **Full context:** read `research/PRD.md` on demand (product spec), plus [`research/viability-analysis.md`](research/viability-analysis.md) and [`research/tech-stack.md`](research/tech-stack.md). Do **not** `@`-import these — they're large; open them when needed.

## 2. Technical Context

### Stack
- **Frontend:** Next.js (App Router) + React + TypeScript. Tailwind v4 + shadcn/ui. **TanStack Query** (server state) + **TanStack Table** (the ranked grid). Web-first responsive *is* the cross-platform strategy; React Native/Expo is v2.
- **Backend/ML:** **Python** (FastAPI for any custom endpoints; mostly a **scheduled worker**). XGBoost / LightGBM / scikit-learn / **SHAP** / pandas / numpy.
- **Database:** **Supabase** (managed Postgres) + Supabase Auth (JWT) + **Row-Level Security**. Reads go through PostgREST/`supabase-js`; the worker writes with the service-role key.
- **Hosting:** Vercel (web) · Modal or Render Cron (worker) · Supabase (DB/Auth/Storage). Budget < $50/mo at MVP.

### Key architectural decisions (rationale — don't reverse without discussion)
- **Two-layer data model.** *Shared* market/model tables (sports, events, odds_snapshots, predictions, ev_bets…) are global, read-only to clients, written only by the worker. *Private* tenant tables (organizations, memberships, tracked_bets, bankrolls, saved_views, alert_rules) are scoped by `org_id` via RLS. One source of truth for odds; per-org isolation for user data.
- **Python backend, not Node.** The value is in Python-only libs (SHAP, gradient boosting, devig/calibration). This is why the backend isn't Node and why **tRPC is not used** (needs end-to-end TS).
- **Worker, not request-server.** Heavy compute is a batch job that fills tables; the client reads results. Keeps cost near zero.
- **The odds API bills CREDITS, not requests** (markets × regions per call; historical 10×). Ingestion must be credit-budget-aware and cache snapshots. This — not hosting — is the dominant cost.

### Coding standards / conventions
- **Odds are American integers** everywhere (e.g. `-110`, `+240`). Probabilities are floats in (0,1). EV is a fraction (0.043 = +4.3%).
- Python: type hints, small pure functions, docstrings explaining *why*. Tests live in `worker/tests/`.
- TS: strict mode; format currency/odds/pct via the helpers in `web/app/page.tsx`.
- **Keep output ASCII** in worker console prints (Windows cp1252 mangles `•`/`—`).
- Secrets only from `.env` (git-ignored). Never hardcode keys; never put the service-role key in the web bundle.

## 3. Current State

### Built & verified
- **Core math** (`worker/core/devig.py`, `clv.py`, `rationale.py`) — de-vig (multiplicative/power/Shin), EV, fractional Kelly, CLV, rationale generator. **10/10 tests green.**
- **Worker orchestrator** (`worker/run.py`) — `--dry-run` produces a correct ranked +EV table.
- **DB schema** (`supabase/migrations/0001_init.sql`) — shared layer + RLS.
- **Frontend MVP "EDGE"** (`web/`) — polished dark Next.js dashboard: ranked +EV board, edge meters (model vs fair), EV pills, filters (sport/market/min-EV), SHAP rationale, confidence, and localStorage bet **tracking** with a slide-over. Runs standalone on sample data; loads live data when `NEXT_PUBLIC_SUPABASE_*` set. Netlify-ready (`web/netlify.toml`). `npm run build` green.
- **DEPLOYED LIVE** — pushed to `github.com/reesecosta-sketch/EDGE`, deployed on Netlify at **edgesportsbetting.netlify.app** (root `netlify.toml`, `base = "web"`). Connected to Supabase project `ytswtgtojovuohmyoqfw`; frontend defaults to the URL + **publishable** key in `web/lib/supabase.ts` (public by design; committed intentionally). DB has `0001_init.sql` schema + `supabase/seed.sql` (8 demo golf bets); board pulls them live via RLS public-read + an `events(name)` join. Sample data is the graceful fallback if the DB is unreachable. Secret key was rotated by the user.
- **Planning docs** — full set in `research/`: viability, tech-stack, PRD, skills, agents, **roadmap** (6 milestones, M1 = golf CLV gate).
- **Sprint Zero (M0) started** — `git init` on `main`; `.github/workflows/ci.yml` (pytest + dry-run + web build); `.gitignore` verified (no secrets tracked). **Not yet done (needs your creds):** GitHub remote + branch protection, dev Supabase project + `db push`, Vercel link, key rotation, filling `.env`.
- **Agents instantiated** — all 11 from `research/agents.md` now exist as `.claude/agents/*.md`. (May require a Claude Code restart to be invocable by name, since `.claude/agents/` was created mid-session.)
- **`0002_multitenancy.sql` written** — org/membership/tenant tables + `is_org_member()` + RLS + auto-personal-org trigger + `ev_bets.trust_tier`. **Written, not yet applied** (needs the dev Supabase project).

### Live +EV pipeline (model-free line-shopping) — built & tested
- `worker/live.py` + `worker/core/positive_ev.py` + `worker/ingest/odds_api.py:fetch_live`: pull live odds (The Odds API) → de-vig each book → cross-book no-vig **consensus** fair line → flag any book price beating it → write to Supabase (`--write`). 14 tests green; verified via `python -m worker.live --sport mlb --dry-run`. Needs `ODDS_API_KEY` + `DATABASE_URL` (both in git-ignored `.env`) to run live. `0003_live_ev.sql` makes `ev_bets.prediction_id` nullable + registers mlb/soccer/tennis. This is honest +EV (soft-book mispricing vs. market), NOT a predictive model — the model/CLV gate is still the separate big project.

### In progress / not yet real (stubs raise clear errors)
- `worker/models/golf.py` → `_load_training_frame()` needs the real golf feature pipeline; `_explain()` is a placeholder, not real SHAP yet.
- `worker/ingest/odds_api.py` → `fetch_odds()` (live pull + snapshot caching) not implemented; `sample_market()` is real.
- `GolfModel.fit()` must report **walk-forward AUC + CLV** (the gate).
- **`0002_multitenancy.sql`** is written but **unapplied** — apply with `supabase db push` once the dev project exists; then `gen-db-types` and write the RLS isolation test.

### Known issues / tech debt
- Local tooling is **npm**, not pnpm (scripts are identical). Python 3.10, Node 26.
- No CI yet; no live odds integration; golf is the only sport with a (stub) model.

## 4. Agent Instructions

### How to approach this codebase
- The **de-vig → EV → CLV core is the product.** Treat `worker/core/` as high-stakes: a subtle math error silently loses money. Any change there requires `pytest` to stay green.
- Prefer extending the `SportModel` interface (`worker/models/base.py`) over bespoke per-sport code.
- Reuse existing helpers; match surrounding style. Verify a change by running it (`--dry-run`, `pytest`, `npm run build`), not just by reading.

### Always confirm before doing
- Adding a new sport as **"trusted"** (visible as real bets) — requires a passed CLV gate, not just a working model.
- Changing de-vig/EV/Kelly logic, or the market-type handling — confirm intent and keep tests green.
- Schema/RLS changes — RLS is the security boundary; a wrong policy leaks data across orgs.
- Introducing new dependencies, services, or paid API tiers.

### Never do without explicit approval
- **Never add code that auto-places bets.** This product recommends; a human acts. No exceptions.
- **Never compute EV against a raw single-side implied probability.** Always de-vig first (see invariant below).
- Never commit secrets or move the service-role key toward the client.
- Never call the live odds API "to test" (burns credits / needs a rotated key) — use `--dry-run` / `sample_market()`.
- Never point Supabase MCP at production data (dev project only).

### Correctness invariant (the one that must never break)
> EV is computed against the **de-vigged fair line**, and de-vig respects market type: **independent props** (e.g. make-cut, each player's yes vs no) de-vig each selection against *its own* opposite side; **mutually-exclusive markets** (moneyline, N-way outright) de-vig the whole market to sum 1. Getting this wrong fabricates fake +EV — it was already caught once.

## 5. File Structure Map
- `research/` — `viability-analysis.md`, `tech-stack.md`, `PRD.md` (source of truth for product/spec).
- `worker/` — Python.
  - `worker/core/` — **devig.py** (odds math, de-vig, EV, Kelly), **clv.py** (CLV gate), **rationale.py** (SHAP→sentence).
  - `worker/models/` — `base.py` (`SportModel` interface), `golf.py` (first vertical, partly stubbed).
  - `worker/ingest/` — `odds_api.py` (sample real, live stubbed).
  - `worker/run.py` (orchestrator), `db.py` (service-role writer), `config.py` (env), `tests/`.
- `web/` — Next.js. `app/page.tsx` (dashboard), `lib/` (`supabase.ts`, `useEvBets.ts`, `types.ts`).
- `supabase/migrations/` — SQL migrations; schema is source-of-truth in git (`0001_init.sql`; `0002` = multitenancy, TODO).
- **Naming:** migrations `NNNN_description.sql`; Python `snake_case`; React components `PascalCase`; markets use snake_case ids (`make_cut`, `top_10`, `moneyline`).

## 6. External Dependencies
| Service | Purpose | Docs |
|---|---|---|
| Supabase | Postgres + Auth + RLS + Storage; official MCP | https://supabase.com/docs |
| The Odds API | Live/historical odds (credit-billed) | https://the-odds-api.com/ |
| Vercel | Frontend hosting | https://vercel.com/docs |
| Modal / Render | Scheduled Python worker | https://modal.com/docs · https://render.com/docs |
| CollegeFootballData, balldontlie | Sport stats (later sports) | https://collegefootballdata.com · https://balldontlie.io |
| Sentry | Error tracking (planned) | https://docs.sentry.io |

**Env vars (names only — values live in `.env`, git-ignored):** `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`, `ODDS_API_KEY`, `ODDS_API_BASE`, `CFBD_API_KEY`, `BALLDONTLIE_API_KEY`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`. **Any key ever pasted into chat/docs must be rotated.**

## 7. User Avatar Reminder
- **Who:** "Alex" — a numerate, self-directed serious bettor (often builds their own models). Secondary: a syndicate/community lead running an org for a group.
- **Wants:** *fewer, better, explained* bets — not more picks. Trusts numbers only when they can see the de-vig and the drivers. Measures themselves by CLV.
- **Fears:** hidden vig, self-deception, black boxes, undisciplined staking, being limited by books.
- **UX principles:** correctness over volume; every bet explained in 1–2 sentences; ranked by EV; fast (dashboard < 2.5s); green is never the *only* signal (accessibility); persistent "decision support, not betting/financial advice" disclaimer.

## Common commands
```bash
# Worker (from worker/)
pip install -r requirements.txt
python -m worker.run --sport golf --dry-run   # ranked +EV table, no DB/keys
pytest -q                                      # core math tests (keep green)
# Web (from web/) — npm locally, not pnpm
npm install && npm run dev
npm run build                                  # typecheck + prod build
```
