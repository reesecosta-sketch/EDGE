# Build Roadmap — EV Sports Platform

**Version:** 1.0 · **Date:** 2026-07-18 · **Author role:** architecture-guardian
**Grounded in:** [`viability-analysis.md`](./viability-analysis.md) · [`tech-stack.md`](./tech-stack.md) · [`PRD.md`](./PRD.md) · [`skills.md`](./skills.md) · [`agents.md`](./agents.md) · [`../.claude/CLAUDE.md`](../.claude/CLAUDE.md)

> **Architectural stance:** The roadmap is deliberately shaped so the project's single biggest risk — *"can a model beat the de-vigged closing line in golf?"* — is answered **early and cheaply (Milestone 1)**, before we invest in the platform around it. If that milestone returns NO-GO, most of Milestones 3–5 should not be built as specified. This is a feature of the plan, not a hedge (viability §4).

---

## 1. MVP Definition

### What the MVP is
The smallest thing that delivers real value to **"Alex"** (numerate serious bettor): **a logged-in web dashboard that shows a daily, ranked list of CLV-validated +EV *golf* bets — each with the de-vigged fair line, EV, a Kelly stake, and a one-sentence SHAP rationale — plus the ability to track a bet and watch personal CLV accumulate.**

The absolute smallest valuable core, in one sentence: **a golf bet list whose edge is proven by positive CLV.** Everything else (auth, dashboard polish, tracking UI) is the delivery vehicle for that core.

### MVP feature set (from PRD §3)
| Feature | In MVP? | Note |
|---|---|---|
| F1 Ingestion pipeline | ✅ | Golf only; credit-aware |
| F2 De-vig→EV→Kelly engine | ✅ | Done + tested |
| F3 Per-sport model | ✅ | **Golf only** |
| F4 CLV validation & tracking | ✅ | The north-star metric; the gate |
| F5 Ranked dashboard | ✅ | Core UI |
| F6 SHAP rationale | ✅ | Real SHAP, not placeholder |
| F7 Filtering / saved views | ◑ | Filters yes; *saved/shared views* deferred |
| F8 Bet tracking & bankroll | ✅ | Personal tracking + CLV/ROI; bankroll minimal |
| F9 Auth + orgs | ◑ | Auth ✅; tenant **schema** built; auto-create a personal org per user; **invite/roles UI deferred** |
| F10 Alerts | ❌ | Post-MVP |
| F11 Responsible-use surface | ✅ | Disclaimer + no auto-place |

### Explicitly deferred to post-MVP
- **Any sport other than golf** (each is its own CLV gate; NFL/CBB sides are *last*, per viability).
- **Syndicate/multi-org UX** — invites, roles, shared views (schema is multi-tenant from day one; the *collaboration UI* waits).
- **Alerts/notifications (F10)**, real-time odds streaming, multi-book line-shopping/arbitrage.
- **Billing/subscriptions**, native mobile app, user-uploaded custom models.
- Full rate-limiting at scale, advanced observability dashboards.

> **Why keep the tenant schema but defer the tenant UX:** getting `org_id` + RLS right is cheap *now* and expensive to retrofit. Building invite flows and role management is not on the critical path to proving value. So we pay the small schema cost early and skip the UX until there's a syndicate asking for it.

---

## 2. Milestone Structure

Durations are **engineering-effort estimates** (align with tech-stack §4: CLV harness 1–3 wks; one-sport MVP 4–8 wks after the gate). Calendar time depends on staffing; a solo builder should read these as sequential.

### M0 — Sprint Zero: Foundation `~3–5 days`
- **Deliverables:** git repo initialized + branch strategy; **dev** Supabase project provisioned with `0001_init.sql` applied; `.env` filled from `.env.example` (keys rotated); CI pipeline green (lint + `pytest` + `npm run build` + worker `--dry-run`); Vercel project linked; agent definition files authored under `.claude/agents/`.
- **Agents:** `devops-agent` (CI, provisioning wiring, Vercel link) · `data-agent` (dev DB + apply 0001) · `security-compliance-agent` (secrets baseline + rotation verification) · `architecture-guardian` (agent files + this roadmap).
- **Dependencies:** none.
- **Success criteria:** a throwaway PR runs **green CI** (10/10 pytest, `npm run build` passes, `--dry-run` runs); dev DB shows schema 0001; `env-secrets-check` finds no committed secret; no exposed key remains un-rotated.

### M1 — Golf CLV Gate (GO / NO-GO) `~2–3 wks` ⛔ HARD GATE
- **Deliverables:** golf feature pipeline wired into `GolfModel._load_training_frame()`; calibrated golf model for make-cut / top-10 with **walk-forward** metrics; historical **opening + closing** odds ingested to Parquet in Supabase Storage; `clv-backtest-harness` producing a CLV report (beat-rate, mean CLV, calibration); real `shap.TreeExplainer` rationale.
- **Agents:** `modeling-agent` (owns) · `backend-agent` (historical odds + stats pulls) · `data-agent` (Parquet storage) · `qa-agent` (tests, keep core green).
- **Dependencies:** M0.
- **Success criteria:** CLV report over **≥ 300 out-of-sample golf bets**; **GO** if mean CLV > 0 and beat-rate materially > 50% with acceptable calibration; **NO-GO otherwise → stop or pivot before building the platform.** This decision escalates to the human (modeling-agent never promotes autonomously).

### M2 — Data & Tenancy Foundation `~1–2 wks` (may overlap late M1)
- **Deliverables:** `0002_multitenancy.sql` (organizations, memberships+roles, tracked_bets, bankrolls, saved_views, alert_rules, `is_org_member()`, RLS default-deny + member policies); `trust_tier` on `ev_bets`; auto-create a personal org on signup; Supabase Auth wired in Next.js; `gen-db-types`; **RLS cross-org isolation test suite green**.
- **Agents:** `data-agent` (owns) · `security-compliance-agent` (RLS review) · `qa-agent` (isolation tests) · `backend-agent` (auth + minimal org bootstrap).
- **Dependencies:** M0. **Proceed past M2 only if M1 = GO.**
- **Success criteria:** two-JWT isolation test proves org A cannot read/write org B; sign-in/out works; types regenerated and committed; architecture-guardian confirms two-layer integrity.

### M3 — Live Ingestion & Serving Pipeline `~2 wks`
- **Deliverables:** credit-aware **live** golf odds ingestion (`fetch_odds`) writing immutable `odds_snapshots`; scheduled worker (Modal/Render) running the golf model and writing ranked `ev_bets` with EV/Kelly/rationale; worker alerting + a "last successful run" heartbeat; structured logging.
- **Agents:** `backend-agent` (ingestion) · `devops-agent` (schedule, alerting, logging) · `modeling-agent` (predict path) · `data-agent` (writes/indexes).
- **Dependencies:** M1 (GO) + M2.
- **Success criteria:** a scheduled run pulls golf odds **within the credit budget**, writes ranked `ev_bets` to dev, exposes a fresh heartbeat, and a forced failure triggers an alert; no re-fetch of unchanged windows.

### M4 — Dashboard & Bet Tracking `~2–3 wks`
- **Deliverables:** ranked dashboard (F5) reading **live** `ev_bets`; per-bet rationale (F6); sport/market/min-EV filters (F7 minimal); one-click bet tracking + personal **CLV/ROI** view (F8/F4); responsible-use disclaimer (F11).
- **Agents:** `frontend-agent` (owns) · `backend-agent` (`/bets/track`, `/clv/summary`) · `qa-agent` (e2e) · `data-agent` (query/index tuning).
- **Dependencies:** M3.
- **Success criteria:** a logged-in user sees live ranked golf bets, filters them, tracks a bet, and sees CLV accumulate; e2e flow green; `npm run build` green; disclaimer present on all surfaces.

### M5 — Hardening & Launch `~1–2 wks`
- **Deliverables:** security review pass (RLS isolation, secrets, **no auto-place path**); WCAG 2.1 AA audit fixes; responsive to 360px; performance benchmarks met; production deploy (web + worker) behind a CI gate; docs / `CLAUDE.md` §3 / memory synced; launch checklist complete (§5).
- **Agents:** `security-compliance-agent` (review/gate) · `frontend-agent` (a11y/responsive) · `devops-agent` (prod deploy, CI gate) · `qa-agent` (perf/e2e) · `docs-agent` (sync).
- **Dependencies:** M4.
- **Success criteria:** every item in the Launch Checklist (§5) green; production URLs live; security-compliance-agent issues a "pass"; docs reflect real state.

**Total effort estimate to MVP:** ~**9–13 weeks** of engineering, gated at M1.

---

## 3. Sprint Zero Checklist

What must be true before we write feature code. ✅ = doable locally now · 🔑 = requires your credentials / an account (I can't create accounts or enter credentials — those are yours per the operating rules).

### Repository setup
- ✅ `git init`, `main` branch, `.gitignore` in place (secrets ignored).
- 🔑 Create the GitHub remote + push; enable branch protection (require green CI to merge).

### CI/CD pipeline
- ✅ `.github/workflows/ci.yml`: lint + `pytest` (worker) + `npm run build` (web) + worker `--dry-run` on every PR.
- 🔑 Add repo secrets in GitHub (dev Supabase URL/keys) so CI can run DB-touching tests.

### Development environment
- ✅ `worker/requirements.txt` + `web/package.json` install cleanly (verified: 10/10 tests, build green).
- ✅ Documented commands in READMEs (`--dry-run`, `pytest`, `npm run dev/build`).
- 🔑 Supabase CLI installed + logged in for migrations.

### Database provisioning
- 🔑 Create a **dev** Supabase project (never point MCP/dev work at prod).
- ✅ `supabase/migrations/0001_init.sql` ready to apply; `0002_multitenancy.sql` scaffolded (M2).
- 🔑 `supabase db push` against the dev project.

### Authentication scaffolding
- ✅ Supabase Auth client pattern documented (anon key in web; service-role server-side only).
- 🔑 Enable auth providers (email + Google) in the Supabase dashboard.

### Secrets & keys
- 🔑 **Rotate every key ever pasted in chat** (balldontlie, prop-line ×2, TheRundown, CFBD) and fill `.env`.
- ✅ `env-secrets-check` baseline: `.env` git-ignored, no key committed, service-role key server-side only.

### Agent scaffolding
- ✅ Author `.claude/agents/*.md` from agents.md (start with `modeling`, `data`, `security-compliance`, `qa`).

---

## 4. Risk Register

| # | Risk | Milestone | Likelihood | Impact | Mitigation |
|---|---|---|---|---|---|
| R1 | **Golf model can't beat the closing line (no CLV)** | M1 | Medium | **Fatal** | This is *why M1 is first and cheap.* Fail fast; if NO-GO, stop/pivot before platform spend. Not a bug — the point of the gate. |
| R2 | **Historical closing odds are hard/expensive to source** | M1 | High | High | Scope the data buy early in M0; start with one tour/market; store as Parquet once. Biggest *data* risk. |
| R3 | Odds-API credit burn blows the budget | M3 | Medium | Med | Credit-aware ingestion; cache snapshots; never re-fetch a window; budget cap + alert. Track spend in logs. |
| R4 | Data leakage / calibration bug fakes an edge | M1–M3 | Medium | High | Strict walk-forward (no shuffle); calibration check; the market-type de-vig invariant + green core tests; CLV as the real judge. |
| R5 | Cross-org RLS leak (multi-tenancy) | M2 | Medium | High | Default-deny + `is_org_member()`; security-compliance review + two-JWT isolation tests gate the milestone. |
| R6 | Exposed secret / service-role key in client | M0–M5 | Medium | High | `env-secrets-check` in CI; security agent review before every deploy; rotate shared keys. |
| R7 | Scope creep to multi-sport / syndicate UX | all | High | Med | MVP definition (§1) + meta-coordinator escalates scope beyond PRD §7. Golf-only until CLV proven. |
| R8 | Worker silently dies → stale bets shown as fresh | M3 | Medium | Med | Heartbeat + failed/stale-run alerting; UI shows `flagged_at` age. |
| R9 | Solo-builder bandwidth / estimate slippage | all | High | Med | Milestones are independently shippable; M1 can stop the whole thing early and cheaply. |
| R10 | (Business, out of build scope) bookmaker limits cap real profit | post-launch | High | Med | Out of MVP build; documented in viability §3 — a business reality to plan for, not an engineering task. |

---

## 5. Launch Checklist (verify before shipping)

### Go/No-Go gate
- [ ] **M1 CLV gate = GO** (positive mean CLV + beat-rate > 50% on ≥ 300 OOS golf bets). *If NO-GO, do not launch.*
- [ ] Model calibration within target band (reliability curve reviewed).

### Security review (security-compliance-agent must pass)
- [ ] Cross-org RLS isolation tests green (two-JWT proof).
- [ ] No secret committed; `.env` git-ignored; **service-role key absent from the web bundle**.
- [ ] All previously-shared API keys rotated.
- [ ] **No code path can place a bet** (grep + review).
- [ ] Supabase MCP / dev work never pointed at prod data.

### Performance benchmarks (PRD §6)
- [ ] Dashboard FCP < 1.5s, interactive < 2.5s (mid-range laptop/4G).
- [ ] Dashboard query p95 < 300ms server-side for ≤ 200 ranked rows (indexed).
- [ ] Worker cycle completes within its scheduled window (< ~10 min).

### Accessibility & responsiveness (PRD §6)
- [ ] WCAG 2.1 AA: keyboard nav, focus states, contrast ≥ 4.5:1, semantic tables.
- [ ] **+EV never signaled by color alone** (sign/label present).
- [ ] Usable to 360px; table scrolls in its own container; body never scrolls sideways.

### User testing (the avatar)
- [ ] A test "Alex" signs in, sees ranked golf bets, filters, and understands a rationale in one read.
- [ ] Tracks a bet in ≤ 2 clicks and sees CLV/ROI accumulate.
- [ ] Confirms trust: the de-vigged fair line + drivers are legible and believable.

### Reliability & ops
- [ ] Scheduled worker deployed; heartbeat visible; failure alert verified.
- [ ] Automated DB backups configured; restore path documented.
- [ ] CI blocks merge on red core-math or isolation tests.

### Documentation
- [ ] `CLAUDE.md` §3 (current state) accurate; PRD "current state" updated; memory index synced.
- [ ] API docs generated from OpenAPI; READMEs current.
- [ ] Responsible-use disclaimer + resource link on all surfaces.

---

## 6. Milestone dependency graph
```
M0 Foundation
   └─▶ M1 Golf CLV Gate ⛔ (GO/NO-GO — can stop the project)
          │  (GO only)
          ├─▶ M2 Data & Tenancy   ─┐
          │                        ├─▶ M3 Ingestion & Serving ─▶ M4 Dashboard & Tracking ─▶ M5 Hardening & Launch
          └────────────────────────┘
   (M2 may start against M0 in parallel with M1, but nothing past M2 proceeds unless M1 = GO)
```
