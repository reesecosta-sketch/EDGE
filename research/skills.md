# Skills Inventory — EV Sports Platform

**Version:** 1.0 · **Date:** 2026-07-18 · **Source:** derived from [`PRD.md`](./PRD.md), [`tech-stack.md`](./tech-stack.md), [`viability-analysis.md`](./viability-analysis.md)

## How to read this
Each entry is a candidate **Claude Code skill** — a reusable, on-demand procedure stored at `.claude/skills/<name>/SKILL.md` ([skills docs](https://code.claude.com/docs/en/skills)). A skill is a directory with a `SKILL.md` (YAML frontmatter — `name`, `description`, optional `allowed-tools` / `disable-model-invocation` / `context: fork` — plus markdown instructions), and may bundle scripts, templates, and reference files that load only when invoked. **Best practice:** the `description` states *what it does and when to use it*; keep bodies focused; put long reference material in bundled files.

Ratings: **Simple** (single tool/file, low risk) · **Moderate** (multi-step, some judgment) · **Complex** (high risk, deep domain or cross-cutting).
Priority mirrors the PRD (P0 MVP-critical · P1 important · P2 nice-to-have).

**Legend for "needed?":** ✅ build now · 🔜 fast-follow · 🟡 later / maybe-not (listed per the "better to over-identify" instruction).

---

## Category A — Database Operations

### A1. `supabase-migration` — Author & apply a SQL migration `P0` ✅
- **Description:** Create a new numbered SQL migration, apply it to a **dev** Supabase project, and keep the schema-in-git source of truth consistent. First job: turn the PRD §4 tenant-layer DDL into `supabase/migrations/0002_multitenancy.sql`.
- **Input:** desired schema change (tables/columns/constraints), current migrations in `supabase/migrations/`, dev project ref.
- **Output:** a `NNNN_description.sql` file + successful `supabase db push` against dev; rollback note.
- **Dependencies:** libs/tools: Supabase CLI, `psql`. APIs: Supabase. Skills: → `rls-policy-author`, `gen-db-types` (run after).
- **Docs:** https://supabase.com/docs/guides/cli · https://supabase.com/docs/guides/deployment/database-migrations
- **Complexity:** Moderate.
- **Invocation:** `/supabase-migration add tenant tables from PRD §4` or "create the multitenancy migration."

### A2. `rls-policy-author` — Write & verify Row-Level Security policies `P0` ✅
- **Description:** Author RLS policies enforcing the two-layer model (public read on shared tables; `org_id`-scoped access on tenant tables via `is_org_member()`), then prove isolation. RLS is the security boundary — a wrong policy leaks data across orgs.
- **Input:** table + intended access rule (who can read/write), org/role model.
- **Output:** `create policy …` statements in a migration + a passing isolation test (ties to `rls-isolation-test`).
- **Dependencies:** Supabase/Postgres. Skills: → `supabase-migration`, `rls-isolation-test`.
- **Docs:** https://supabase.com/docs/guides/database/postgres/row-level-security
- **Complexity:** Complex (security-critical).
- **Invocation:** `/rls-policy-author tracked_bets — members of org only`.

### A3. `gen-db-types` — Generate TypeScript types from the schema `P0` ✅
- **Description:** Regenerate `web/lib/types.ts` (currently hand-written) from the live schema so the frontend stays in sync after any migration. Closes the Python↔TS type seam (tech-stack §6).
- **Input:** dev project ref / `DATABASE_URL`.
- **Output:** generated `Database` types committed to `web/lib/`.
- **Dependencies:** Supabase CLI (`supabase gen types typescript`). Skills: runs after `supabase-migration`.
- **Docs:** https://supabase.com/docs/guides/api/rest/generating-types
- **Complexity:** Simple.
- **Invocation:** `/gen-db-types` after a schema change.

### A4. `db-query` — Author a read/aggregate query `P0` ✅
- **Description:** Write a PostgREST/`supabase-js` query or a worker SQL query for a dashboard/CLV need, using the indexing strategy in PRD §4 (e.g. ranked open bets, CLV rollups).
- **Input:** the question (columns, filters, ordering, tenant scope).
- **Output:** query + confirmation it uses an existing index (or a new index proposed).
- **Dependencies:** `supabase-js` / `psycopg`. Skills: may trigger `supabase-migration` for a missing index.
- **Docs:** https://supabase.com/docs/reference/javascript/select · https://postgrest.org/en/stable/references/api.html
- **Complexity:** Simple–Moderate.
- **Invocation:** `/db-query top 200 open golf bets by EV`.

### A5. `seed-data` — Seed reference & sample data `P1` 🔜
- **Description:** Idempotently seed `sports` and load sample `ev_bets`/events for local/dev demos so the dashboard renders without a live worker run.
- **Input:** target env, sample fixtures.
- **Output:** seed SQL/script + populated dev tables.
- **Dependencies:** Supabase CLI / `psycopg`.
- **Docs:** https://supabase.com/docs/guides/local-development/seeding-your-database
- **Complexity:** Simple.
- **Invocation:** `/seed-data dev`.

---

## Category B — Authentication & Authorization

### B1. `supabase-auth-setup` — Wire authentication `P0` ✅
- **Description:** Configure Supabase Auth (email + OAuth), session handling in Next.js, and the browser client (anon key only, never service role). Implements PRD F9 sign-in.
- **Input:** enabled providers, redirect URLs.
- **Output:** working sign-in/out, session context in the web app, protected routes.
- **Dependencies:** `@supabase/supabase-js`, `@supabase/ssr`. APIs: Supabase Auth. Skills: → `org-membership-flow`.
- **Docs:** https://supabase.com/docs/guides/auth · https://supabase.com/docs/guides/auth/server-side/nextjs
- **Complexity:** Moderate.
- **Invocation:** `/supabase-auth-setup email + google`.

### B2. `org-membership-flow` — Organizations, roles & invites `P0` ✅
- **Description:** Implement multi-tenant org creation, membership with `owner/admin/member` roles, and invite flow (PRD F9 / API §5). Enforces role checks on admin actions.
- **Input:** org/role model (PRD §4), invite delivery method.
- **Output:** org CRUD + invite endpoints/UI; role-gated actions; RLS-backed isolation.
- **Dependencies:** Supabase Auth + DB. Skills: → `rls-policy-author`, `fastapi-endpoint`, `rls-isolation-test`.
- **Docs:** https://supabase.com/docs/guides/auth/managing-user-data
- **Complexity:** Complex.
- **Invocation:** `/org-membership-flow implement create-org + invite`.

---

## Category C — External API Integration

### C1. `odds-api-integration` — Credit-aware odds ingestion `P0` ✅
- **Description:** Implement `worker/ingest/odds_api.py:fetch_odds()` — pull odds, persist immutable `odds_snapshots`, and **respect the credit budget** (credits ≠ requests; markets×regions per call, historical 10×). Never re-fetch an unchanged window. Implements PRD F1.
- **Input:** sport key, markets, regions, per-run credit cap, `ODDS_API_KEY`.
- **Output:** snapshot rows written; credit-spend log; graceful failure + alert.
- **Dependencies:** `httpx`. APIs: **The Odds API** (paid, credit-billed). Skills: → `worker-alerting`, `db-query`.
- **Docs:** https://the-odds-api.com/liveapi/guides/v4/ · https://the-odds-api.com/account/usage-plans.html
- **Complexity:** Complex (cost + reliability).
- **Invocation:** `/odds-api-integration wire fetch_odds for golf`.
- ⚠️ Never call the live API "to test" — use `sample_market()`. Requires a rotated key.

### C2. `stats-api-integration` — Sport feature pulls `P1` 🔜
- **Description:** Pull sport-specific stats (golf SG data; later CFBD, balldontlie) into the feature pipeline that feeds `SportModel._load_training_frame()`.
- **Input:** source, endpoints, entity mapping to `players`/`events`.
- **Output:** normalized feature rows / cached raw responses.
- **Dependencies:** `httpx`, `pandas`. APIs: CollegeFootballData, balldontlie, golf data source. Skills: → `sport-model-scaffold`.
- **Docs:** https://collegefootballdata.com/ · https://docs.balldontlie.io/
- **Complexity:** Moderate.
- **Invocation:** `/stats-api-integration connect golf SG features`.

### C3. `fastapi-endpoint` — Scaffold a REST action endpoint `P0` ✅
- **Description:** Generate a FastAPI endpoint (Pydantic request/response, JWT auth dependency, error envelope, OpenAPI doc) per API §5 (e.g. `/bets/track`, `/clv/summary`).
- **Input:** route, method, auth level, request/response shape.
- **Output:** typed handler + test + auto OpenAPI entry.
- **Dependencies:** `fastapi`, `pydantic`, `uvicorn`. Skills: → `python-test-author`, `rate-limiter`, `api-doc-gen`.
- **Docs:** https://fastapi.tiangolo.com/ · https://docs.pydantic.dev/
- **Complexity:** Moderate.
- **Invocation:** `/fastapi-endpoint POST /api/v1/bets/track`.

### C4. `rate-limiter` — Request rate limiting `P1` 🔜
- **Description:** Add per-IP/per-user rate limits (PRD §5 table) at FastAPI middleware and/or the edge, returning `429` + `Retry-After`.
- **Input:** limits per surface.
- **Output:** middleware + tests for limit + reset.
- **Dependencies:** `slowapi`/`fastapi-limiter` (+ Redis if distributed). Skills: → `fastapi-endpoint`.
- **Docs:** https://slowapi.readthedocs.io/ · https://vercel.com/docs/edge-network/rate-limiting
- **Complexity:** Moderate.
- **Invocation:** `/rate-limiter apply PRD §5 limits`.

---

## Category D — Predictive Modeling & the EV Core (domain — the heart)

### D1. `ev-math-guardrail` — Verify/extend the de-vig→EV→Kelly core `P0` ✅
- **Description:** Safely change or extend `worker/core/devig.py` while preserving the correctness invariant: **EV vs. the de-vigged fair line, market-type-aware** (independent props vs. mutually-exclusive). Any edit keeps `pytest` green.
- **Input:** the proposed math change; existing tests.
- **Output:** change + expanded tests; confirmation of the invariant.
- **Dependencies:** stdlib + `pytest`. Skills: → `python-test-author`.
- **Docs:** (internal) `worker/core/devig.py`; background: https://www.pinnacle.com/en/betting-articles/Betting-Strategy/removing-the-margin-and-calculating-fair-odds/
- **Complexity:** Complex (silent-money-loss risk).
- **Invocation:** `/ev-math-guardrail add additive devig method`.

### D2. `sport-model-scaffold` — Implement a new `SportModel` `P0` (golf) / `P1` (others) ✅
- **Description:** Implement the `SportModel` interface for a sport: feature frame, gradient-boosted + **calibrated** classifier, field-normalization, strict **walk-forward** validation (PRD F3). First real target: `GolfModel._load_training_frame()`.
- **Input:** sport, target markets, feature source.
- **Output:** a `models/<sport>.py` producing calibrated probabilities + reported metrics.
- **Dependencies:** `xgboost`, `lightgbm`, `scikit-learn`, `pandas`, `numpy`. Skills: → `stats-api-integration`, `calibration-check`, `clv-backtest-harness`, `shap-rationale`.
- **Docs:** https://xgboost.readthedocs.io/ · https://lightgbm.readthedocs.io/ · https://scikit-learn.org/stable/modules/calibration.html
- **Complexity:** Complex.
- **Invocation:** `/sport-model-scaffold golf make_cut,top_10`.

### D3. `clv-backtest-harness` — The CLV go/no-go gate `P0` ✅
- **Description:** Build the harness that runs a sport's model as-of pre-close over historical events, de-vigs the closing line, and reports **beat-rate + mean CLV** (viability §4). A sport is not "trusted" until this passes.
- **Input:** historical opening + **closing** odds (Parquet), model, sample window.
- **Output:** CLV report (beat-rate, mean CLV, calibration) + trust-tier recommendation.
- **Dependencies:** `worker/core/clv.py`, `pandas`. Skills: → `sport-model-scaffold`, `calibration-check`.
- **Docs:** (internal) `worker/core/clv.py`
- **Complexity:** Complex.
- **Invocation:** `/clv-backtest-harness golf top_10`.

### D4. `shap-rationale` — Real SHAP explanations `P0` ✅
- **Description:** Replace `GolfModel._explain()` placeholder with `shap.TreeExplainer` to extract per-selection top drivers feeding the 1–2 sentence rationale (PRD F6).
- **Input:** trained model, feature row for a selection.
- **Output:** top-3 signed drivers → `shap_top` JSON → rationale string.
- **Dependencies:** `shap`. Skills: uses `worker/core/rationale.py`.
- **Docs:** https://shap.readthedocs.io/en/latest/ · https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html
- **Complexity:** Moderate.
- **Invocation:** `/shap-rationale wire real SHAP for golf`.

### D5. `calibration-check` — Reliability/calibration report `P1` 🔜
- **Description:** Produce reliability curves + calibration error for a model's probabilities (EV is meaningless if probabilities aren't calibrated). PRD F3 acceptance criterion.
- **Input:** out-of-sample predictions + outcomes.
- **Output:** reliability plot + Brier/ECE numbers stored in `model_runs.metrics`.
- **Dependencies:** `scikit-learn`, `matplotlib`.
- **Docs:** https://scikit-learn.org/stable/modules/calibration.html
- **Complexity:** Moderate.
- **Invocation:** `/calibration-check golf make_cut`.

---

## Category E — Frontend Component Generation

### E1. `nextjs-component` — Generate a React/TS component `P0` ✅
- **Description:** Scaffold a Next.js App-Router component following project conventions (TanStack Query for data, TanStack Table for grids, Tailwind + shadcn, formatting helpers). Server-state via Query, small local state only.
- **Input:** component purpose, data source, props.
- **Output:** typed `.tsx` component wired to `useEvBets`-style hooks.
- **Dependencies:** `next`, `react`, `@tanstack/react-query`, `@tanstack/react-table`, `tailwindcss`. Skills: → `gen-db-types`, `a11y-audit`.
- **Docs:** https://nextjs.org/docs · https://tanstack.com/query · https://tanstack.com/table · https://ui.shadcn.com
- **Complexity:** Moderate.
- **Invocation:** `/nextjs-component CLV performance chart`.

### E2. `dashboard-filter-view` — Filters & saved views `P1` 🔜
- **Description:** Add/extend dashboard filters (sport/market/min-EV) and persist per-user **saved views** (PRD F7), org-shareable.
- **Input:** filter dimensions, persistence rules.
- **Output:** filter UI + `saved_views` read/write with RLS.
- **Dependencies:** TanStack Query, `supabase-js`; optionally Zustand. Skills: → `db-query`, `rls-policy-author`.
- **Docs:** https://zustand.docs.pmnd.rs/ · https://tanstack.com/query
- **Complexity:** Moderate.
- **Invocation:** `/dashboard-filter-view add saved views`.

### E3. `a11y-audit` — Accessibility check (WCAG 2.1 AA) `P1` 🔜
- **Description:** Audit/fix a component for the NFR standard: keyboard nav, focus states, contrast ≥ 4.5:1, semantic table markup, **color-not-the-only-signal** for +EV, `prefers-reduced-motion`.
- **Input:** target component/page.
- **Output:** audit findings + fixes; automated check passing.
- **Dependencies:** `@axe-core/react`, eslint-plugin-jsx-a11y.
- **Docs:** https://www.w3.org/WAI/WCAG21/quickref/ · https://github.com/dequelabs/axe-core
- **Complexity:** Moderate.
- **Invocation:** `/a11y-audit dashboard table`.

### E4. `responsive-check` — Mobile responsiveness `P1` 🔜
- **Description:** Verify layouts down to 360px: table scrolls in its own container (body never scrolls sideways), touch targets ≥ 44px, filters collapse to a sheet (NFR mobile).
- **Input:** page/component.
- **Output:** responsive fixes + viewport screenshots.
- **Dependencies:** browser preview tooling.
- **Docs:** https://nextjs.org/docs/app/building-your-application/styling
- **Complexity:** Simple–Moderate.
- **Invocation:** `/responsive-check dashboard`.

---

## Category F — Testing & Validation

### F1. `python-test-author` — Author pytest tests `P0` ✅
- **Description:** Write/extend pytest coverage for the worker, prioritizing the EV-core invariants (odds conversion, all devig methods, EV sign, Kelly caps, CLV). Guardrail: core math suite stays 100% green.
- **Input:** target module/behavior.
- **Output:** tests in `worker/tests/` + green run.
- **Dependencies:** `pytest`. Skills: pairs with `ev-math-guardrail`.
- **Docs:** https://docs.pytest.org/
- **Complexity:** Simple–Moderate.
- **Invocation:** `/python-test-author cover Shin devig edge cases`.

### F2. `rls-isolation-test` — Cross-org data-leak tests `P0` ✅
- **Description:** Automated tests proving a user in org A cannot read/write org B's tenant rows (the security guardrail). Runs as two JWT contexts against dev.
- **Input:** tenant tables + policies.
- **Output:** passing isolation test suite; failure blocks deploy.
- **Dependencies:** `pytest` + `supabase-py` or SQL harness. Skills: → `rls-policy-author`.
- **Docs:** https://supabase.com/docs/guides/database/postgres/row-level-security#testing-policies
- **Complexity:** Complex.
- **Invocation:** `/rls-isolation-test tenant tables`.

### F3. `e2e-test` — End-to-end dashboard tests `P1` 🔜
- **Description:** Playwright flows: load dashboard, sort/filter, sign in, track a bet, verify rationale renders and sample-vs-live states.
- **Input:** user flow to cover.
- **Output:** Playwright spec + CI run.
- **Dependencies:** `@playwright/test`.
- **Docs:** https://playwright.dev/docs/intro
- **Complexity:** Moderate.
- **Invocation:** `/e2e-test track-a-bet flow`.

### F4. `build-verify` — Full local verification `P0` ✅
- **Description:** One command to prove a change is sound: worker `--dry-run` + `pytest` + web `npm run build` (typecheck). The go-before-commit gate. Overlaps the bundled `/verify`.
- **Input:** none (whole repo).
- **Output:** pass/fail report of all three checks.
- **Dependencies:** python, node/npm. Skills: none.
- **Docs:** (internal) READMEs; bundled https://code.claude.com/docs/en/commands
- **Complexity:** Simple.
- **Invocation:** `/build-verify` (or the bundled `/verify`).

---

## Category G — Deployment & Infrastructure

### G1. `worker-deploy` — Deploy the scheduled worker `P0` ✅
- **Description:** Package and schedule the Python ingestion/model worker on Modal (or Render Cron), with secrets, idempotent runs, and a cadence per sport.
- **Input:** schedule, env secrets, entrypoint.
- **Output:** deployed scheduled job + run logs.
- **Dependencies:** Modal SDK / Render. Skills: → `env-secrets-check`, `worker-alerting`.
- **Docs:** https://modal.com/docs/guide/cron · https://render.com/docs/cronjobs
- **Complexity:** Moderate.
- **Invocation:** `/worker-deploy golf every 6h on Modal`.

### G2. `vercel-deploy` — Deploy the web app `P0` ✅
- **Description:** Configure the Next.js app on Vercel: env vars (public Supabase keys only), preview/prod, build settings.
- **Input:** project, env vars.
- **Output:** deployed preview/prod URLs.
- **Dependencies:** Vercel (official MCP available). Skills: → `env-secrets-check`.
- **Docs:** https://vercel.com/docs/deployments · https://vercel.com/docs/projects/environment-variables
- **Complexity:** Simple–Moderate.
- **Invocation:** `/vercel-deploy production`.

### G3. `ci-pipeline` — CI/CD with GitHub Actions `P1` 🔜
- **Description:** Author the CI workflow: lint + `pytest` + `npm run build` + `rls-isolation-test` on PR; apply migrations to dev; deploy on merge. Blocks merge on red core-math tests.
- **Input:** jobs to run, secrets.
- **Output:** `.github/workflows/*.yml` + green pipeline.
- **Dependencies:** GitHub Actions (official MCP). Skills: → `build-verify`, `rls-isolation-test`.
- **Docs:** https://docs.github.com/en/actions
- **Complexity:** Moderate.
- **Invocation:** `/ci-pipeline set up PR checks`.

### G4. `env-secrets-check` — Secrets & env hygiene `P0` ✅
- **Description:** Verify all secrets come from `.env`/platform env, the **service-role key never enters the web bundle**, `.env` is git-ignored, and no key is committed. Flags exposed keys for rotation.
- **Input:** repo tree, env references.
- **Output:** pass/fail report + list of anything to rotate/move.
- **Dependencies:** `gitleaks`/`trufflehog` (optional). Skills: none.
- **Docs:** https://github.com/gitleaks/gitleaks · https://supabase.com/docs/guides/api/api-keys
- **Complexity:** Simple.
- **Invocation:** `/env-secrets-check`.

### G5. `db-backup-restore` — Backup & migration safety `P1` 🔜
- **Description:** Configure automated backups (+ `pg_dump` to object storage on free tier) and a documented restore/rollback path (NFR reliability).
- **Input:** schedule, storage target.
- **Output:** backup job + tested restore runbook.
- **Dependencies:** Supabase backups, `pg_dump`.
- **Docs:** https://supabase.com/docs/guides/platform/backups
- **Complexity:** Moderate.
- **Invocation:** `/db-backup-restore configure nightly`.

---

## Category H — Documentation Generation

### H1. `api-doc-gen` — API reference from OpenAPI `P1` 🔜
- **Description:** Generate/refresh API docs from FastAPI's OpenAPI schema and (optionally) a typed TS client for the frontend.
- **Input:** FastAPI app.
- **Output:** OpenAPI JSON + rendered docs / generated client.
- **Dependencies:** `fastapi` (built-in OpenAPI), `openapi-typescript`.
- **Docs:** https://fastapi.tiangolo.com/features/ · https://github.com/openapi-ts/openapi-typescript
- **Complexity:** Simple.
- **Invocation:** `/api-doc-gen`.

### H2. `docs-sync` — Keep research docs & CLAUDE.md current `P1` 🔜
- **Description:** After a milestone, update PRD "current state," `CLAUDE.md` §3, and READMEs so the persistent context matches reality (avoids stale memory).
- **Input:** what changed this session.
- **Output:** updated docs + memory index.
- **Dependencies:** none. Skills: none.
- **Docs:** https://code.claude.com/docs/en/memory
- **Complexity:** Simple.
- **Invocation:** `/docs-sync after golf model lands`.

---

## Category I — Error Handling & Logging

### I1. `sentry-integration` — Error tracking `P1` 🔜
- **Description:** Instrument the worker and web app with Sentry (no secrets in breadcrumbs); surface errors for triage (official Sentry MCP).
- **Input:** DSN, environments.
- **Output:** captured errors + release tagging.
- **Dependencies:** `sentry-sdk` (Python), `@sentry/nextjs`.
- **Docs:** https://docs.sentry.io/platforms/python/ · https://docs.sentry.io/platforms/javascript/guides/nextjs/
- **Complexity:** Simple–Moderate.
- **Invocation:** `/sentry-integration worker + web`.

### I2. `structured-logging` — Consistent logs `P1` 🔜
- **Description:** Standardize structured (JSON) logging in the worker (ingestion counts, credit spend, run duration, idempotency keys) so failures are diagnosable.
- **Input:** modules to instrument.
- **Output:** logging config + consistent log calls.
- **Dependencies:** `structlog` or stdlib `logging`.
- **Docs:** https://www.structlog.org/ · https://docs.python.org/3/library/logging.html
- **Complexity:** Simple.
- **Invocation:** `/structured-logging worker ingestion`.

### I3. `worker-alerting` — Alert on failed/stale runs `P0` ✅
- **Description:** Alert when a scheduled run fails, times out, or produces no bets (reliability NFR). Prevents a silently dead pipeline serving stale bets.
- **Input:** failure conditions, channel.
- **Output:** alert on failure + a "last successful run" heartbeat surfaced in the UI.
- **Dependencies:** Sentry / email. Skills: → `sentry-integration`, `worker-deploy`.
- **Docs:** https://docs.sentry.io/product/crons/ · https://modal.com/docs/guide/cron
- **Complexity:** Moderate.
- **Invocation:** `/worker-alerting on failed golf run`.

---

## Category J — Product / Compliance (cross-cutting)

### J1. `alert-rules-engine` — User bet alerts (PRD F10) `P2` 🟡
- **Description:** Per-user alert rules (sport/market/min-EV) → email/web-push when a new qualifying `ev_bet` appears. Explicitly out of MVP scope; listed for completeness.
- **Input:** rule model, delivery channel.
- **Output:** rule CRUD + worker emit + delivery.
- **Dependencies:** email provider / Web Push; `alert_rules` table.
- **Docs:** https://developer.mozilla.org/en-US/docs/Web/API/Push_API
- **Complexity:** Complex.
- **Invocation:** `/alert-rules-engine` (v2).

### J2. `responsible-use-surface` — Compliance UI (PRD F11) `P0` ✅
- **Description:** Ensure the persistent "decision support, not betting/financial advice" disclaimer + responsible-gambling link appear on all surfaces, and that **no auto-placement code path exists**.
- **Input:** page inventory.
- **Output:** disclaimer components + a check that fails if auto-placement appears.
- **Dependencies:** none.
- **Docs:** (internal) PRD §6 compliance.
- **Complexity:** Simple.
- **Invocation:** `/responsible-use-surface audit`.

### J3. `bet-tracking-clv-ui` — Track bets & CLV dashboard (PRD F8) `P1` 🔜
- **Description:** One-click "track this bet," settlement, and a personal/org CLV + ROI view — the scoreboard that is the product's north-star metric.
- **Input:** `ev_bet` row, stake, book.
- **Output:** tracked-bet write + CLV/ROI UI (org-scoped).
- **Dependencies:** `fastapi-endpoint` (`/bets/track`, `/clv/summary`), `nextjs-component`, `db-query`.
- **Docs:** (internal) PRD F4/F8, `worker/core/clv.py`.
- **Complexity:** Complex.
- **Invocation:** `/bet-tracking-clv-ui`.

---

## Priority summary

| Priority | Skills |
|---|---|
| **P0 — MVP-critical ✅** | A1 supabase-migration · A2 rls-policy-author · A3 gen-db-types · A4 db-query · B1 supabase-auth-setup · B2 org-membership-flow · C1 odds-api-integration · C3 fastapi-endpoint · D1 ev-math-guardrail · D2 sport-model-scaffold · D3 clv-backtest-harness · D4 shap-rationale · E1 nextjs-component · F1 python-test-author · F2 rls-isolation-test · F4 build-verify · G1 worker-deploy · G2 vercel-deploy · G4 env-secrets-check · I3 worker-alerting · J2 responsible-use-surface |
| **P1 — important 🔜** | A5 seed-data · C2 stats-api-integration · C4 rate-limiter · D5 calibration-check · E2 dashboard-filter-view · E3 a11y-audit · E4 responsive-check · F3 e2e-test · G3 ci-pipeline · G5 db-backup-restore · H1 api-doc-gen · H2 docs-sync · I1 sentry-integration · I2 structured-logging · J3 bet-tracking-clv-ui |
| **P2 — later / maybe-not 🟡** | J1 alert-rules-engine |

## The critical path (build these first, in order)
1. **D1 ev-math-guardrail** + **F1 python-test-author** — protect the core (already green; keep it that way).
2. **D2 sport-model-scaffold** + **C2 stats** + **D5 calibration** + **D3 clv-backtest-harness** — the **CLV gate** for golf. *If this fails, stop — nothing downstream matters (viability §4).*
3. **A1/A2/A3 schema + RLS + types** and **F2 rls-isolation-test** — the multi-tenant foundation.
4. **C1 odds-api-integration** + **I3 worker-alerting** — live data, safely and within budget.
5. **B1/B2 auth + orgs**, **C3 endpoints**, **E1 dashboard**, **J3 tracking/CLV UI** — the usable product.
6. **G1/G2/G4 deploy + secrets**, then **G3 CI**, observability (**I1/I2**), and polish (**E3/E4**).

> **Note on scope:** D2/D3 (the CLV gate for golf) gate everything. A dozen of these skills can be built, but if golf can't beat the closing line, the right move is to stop before the platform work — exactly as the viability analysis concluded.
