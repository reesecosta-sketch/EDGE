# Product Requirements Document — EV Sports Platform

**Version:** 1.0 · **Date:** 2026-07-18 · **Status:** Draft for build
**Companion docs:** [`viability-analysis.md`](./viability-analysis.md) · [`tech-stack.md`](./tech-stack.md)

> **Reader orientation.** This product surfaces a daily, ranked dashboard of positive-expected-value (+EV) bets and explains *why* each is +EV. It is **decision support** — it never places bets. The entire product rests on one testable claim: that a model can beat the **de-vigged closing line** (positive Closing Line Value). If that claim fails for a sport, that sport has no product. Every requirement below is downstream of that fact.

---

## 1. Executive Summary

**What we're building.** A web application that ingests live sportsbook odds and sport-specific statistics, runs calibrated predictive models to estimate the *true* probability of outcomes, compares that estimate against the **de-vigged fair line** from sharp markets, and presents a daily, auto-ranked dashboard of the highest positive-EV bets. Every recommendation carries a one-to-two sentence, SHAP-derived rationale naming the top statistical drivers. The product starts with **golf** (a structurally soft, prop-rich market) and expands to additional sports only after each clears a **Closing Line Value (CLV) validation gate**.

**Primary value proposition.** *"See only the bets where the math is actually on your side — and know exactly why."* We replace gut, touts, and hand-built spreadsheets with a disciplined, explainable, CLV-validated edge screen. The differentiator is not "more picks" — it is **honesty**: correct de-vig math, transparent reasoning, and a refusal to show edge we can't defend.

**Target user persona (psychographic).** **"Alex," the quantitatively-minded serious bettor.** Alex is 28–45, numerate (often builds their own spreadsheets or Python models), and treats betting as an *intellectual and financial optimization problem*, not entertainment.
- **Motivations:** beating an efficient market is a puzzle worth solving; a validated edge is both pride and supplemental income; process and discipline over action.
- **Fears:** losing money to hidden vig they didn't model; getting their edge quietly eroded; tilt and undisciplined staking; being limited/banned by books; following a "black box" they can't interrogate; wasting hours in spreadsheets that may be self-deluding.
- **Goals:** find genuine +EV faster than they can by hand; *trust* the numbers because they can see the de-vig and the drivers; track their CLV to know whether they actually have an edge; stake sizes rationally (Kelly), not emotionally.

Alex does not want more noise. Alex wants **fewer, better, explained** bets and a scoreboard (CLV) that tells the truth.

---

## 2. User Avatar Deep Dive

### Who exactly is this for?
1. **Primary — the individual power-bettor ("Alex").** Self-directed, spreadsheet/model-literate, bets across a handful of books, cares about edge and CLV. Willing to pay a monthly subscription that costs less than one avoided bad bet.
2. **Secondary — the small syndicate / community lead ("the capper").** Runs a betting group, Discord, or informal syndicate. Needs to share a curated board with members, manage who sees what, and track group performance. **This is why the product is multi-tenant: an "organization" is a syndicate, community, or household of bettors** sharing a private workspace over the shared market data.

### Their current painful workflow (today, without us)
1. Manually pull odds from 3–6 books across browser tabs.
2. Maintain a fragile spreadsheet or script that maybe removes vig (often incorrectly — comparing to one side's raw implied prob).
3. Eyeball which lines look "off," second-guess whether it's edge or noise.
4. No systematic record of **CLV**, so they can't tell if they're actually winning on process or just running hot/cold.
5. Repeat daily, under time pressure, before lines move. **Hours of work, low confidence, easy to self-deceive.**

### What success looks like for them
- Open one dashboard each morning; see a ranked, filtered list of defensible +EV bets in under a minute.
- For any bet, understand *why* in one sentence and trust the de-vig is correct.
- Log a bet in two clicks; watch their **CLV trend** accumulate as objective proof of edge (or lack of it).
- Stake sizes suggested by fractional Kelly, not adrenaline.

### What would make them tell a colleague?
- **"The CLV tracker proved I actually have an edge"** (or, honestly, saved them from believing they did).
- **"It shows the de-vigged fair line, not fake +EV"** — trust earned by correctness.
- **"The one-line explanations are actually right"** — the rationale names drivers they recognize.
- **"It saved me an hour every morning."** Time + trust are the referral engine, not volume of picks.

---

## 3. Feature Specification

Priority: **P0** = MVP-critical (no product without it) · **P1** = important (fast-follow) · **P2** = nice-to-have.
Sport scope for MVP features is **golf-first**; the architecture is multi-sport but only golf must clear the CLV gate for launch.

### F1 — Odds & Stats Ingestion Pipeline `P0`
> As the **system**, I want to pull current odds and sport stats on a schedule so that model outputs reflect live markets.
- **Acceptance criteria:**
  - Scheduled worker fetches odds for enabled sports/markets and writes immutable `odds_snapshots` rows (timestamped).
  - Ingestion is **credit-aware**: respects a configurable per-run budget; never re-fetches an unchanged window (The Odds API bills credits, not requests).
  - A failed run alerts (Sentry) and does not corrupt prior data; writes are idempotent.
- **Technical notes / deps:** Python worker on Modal/Render Cron; The Odds API + stats sources (CFBD, etc.); writes via service-role (bypasses RLS). Depends on schema §4.

### F2 — De-vig → EV → Kelly Engine `P0`
> As the **system**, I want to compute the no-vig fair probability and expected value for every selection so that only genuinely +EV bets surface.
- **Acceptance criteria:**
  - EV is computed against the **de-vigged fair line**, never a single side's raw implied prob.
  - De-vig respects **market type**: independent props (e.g. make-cut) de-vig each selection against its own opposite side; mutually-exclusive markets (moneyline, N-way outright) de-vig the full market to sum 1.
  - Supports multiplicative, power, and **Shin** de-vig methods (configurable).
  - Fractional-Kelly stake is computed and capped; never negative.
  - Unit tests cover odds conversion, all three de-vig methods, EV sign, Kelly caps. *(Already implemented & green — `worker/core/devig.py`, 10 tests.)*
- **Technical notes:** This is the correctness core. Any change requires tests to stay green.

### F3 — Per-Sport Predictive Models `P0` (golf) / `P1` (others)
> As the **system**, I want calibrated per-sport probability models so that "model true probability" is meaningful.
- **Acceptance criteria:**
  - Each sport implements the `SportModel` interface (`fit`, `predict_event`).
  - Probabilities are **calibrated** (isotonic/Platt); reliability curve reported.
  - Golf model outputs make-cut / top-5 / top-10 probabilities, field-normalized where mutually constrained.
  - Training uses strict **walk-forward** validation (train on past, validate on future) — no shuffled leakage.
- **Technical notes:** XGBoost/LightGBM/HistGB + scikit-learn calibration. `worker/models/golf.py` scaffolded; `_load_training_frame()` must connect to the real feature pipeline.

### F4 — Closing Line Value (CLV) Validation & Tracking `P0`
> As **Alex**, I want to see the CLV of flagged and placed bets so that I know whether the edge is real, not luck.
- **Acceptance criteria:**
  - For each flagged bet, capture bet-time no-vig prob and, after close, closing no-vig prob → compute `clv_points`.
  - Dashboard shows aggregate **beat-rate** (% of bets with positive CLV) and **mean CLV** per sport and per user/org.
  - A sport is not promoted from "experimental" to "trusted" until it shows positive mean CLV over a documented sample (gate).
- **Technical notes:** `worker/core/clv.py` implemented & tested; needs the closing-line capture job + `bet_results` writes.

### F5 — Ranked +EV Dashboard `P0`
> As **Alex**, I want a dashboard that ranks all daily bets by EV so that the most profitable opportunities are at the top.
- **Acceptance criteria:**
  - Table lists open `ev_bets` sorted by EV descending by default; columns: sport, market, selection, book, price, model %, fair %, EV, Kelly, rationale.
  - Client-side re-sort by any column; server filters by sport, market, and **minimum EV threshold**.
  - Auto-refreshes at a sensible interval (lines move); shows a "showing sample data" state until the DB is connected.
  - Renders < 1.5 s on a mid-range laptop for ≤ 200 rows.
- **Technical notes:** Next.js + TanStack Query + TanStack Table; reads Supabase via anon key + RLS. *(Scaffolded & building green — `web/app/page.tsx`.)*

### F6 — Per-Bet Explainability (SHAP rationale) `P0`
> As **Alex**, I want a one-to-two sentence reason for each bet so that I never follow a black box.
- **Acceptance criteria:**
  - Every `ev_bet` has a `rationale` naming the top 2–3 drivers (from SHAP) and stating model % vs. fair % and the edge.
  - Rationale is generated deterministically from model outputs (no hallucinated LLM text).
- **Technical notes:** `worker/core/rationale.py` implemented; `GolfModel._explain()` must be swapped from placeholder to real `shap.TreeExplainer`.

### F7 — Filtering & Saved Views `P1`
> As **Alex**, I want to filter by sport / bet type / min-EV and save my preferred view so that I see my niche instantly.
- **Acceptance criteria:** filters persist per user; a saved view restores sport/market/min-EV; shareable within an org.
- **Technical notes:** `saved_views` table, org-scoped by RLS.

### F8 — Bet Tracking & Bankroll `P1`
> As **Alex**, I want to log bets and track my bankroll & CLV so that I measure real performance.
- **Acceptance criteria:** one-click "track this bet" from a row; records stake, price, book; settles to win/loss/push; feeds CLV and ROI; all rows org-scoped and private.
- **Technical notes:** `user_bets` + `bet_results`; RLS locks to `org_id`/`user_id`.

### F9 — Authentication, Organizations & Membership `P0`
> As a **user**, I want to sign in and belong to an organization so that my private data is isolated and shareable with my group.
- **Acceptance criteria:**
  - Email + OAuth sign-in (Supabase Auth).
  - A user belongs to one or more **organizations** with a **role** (owner/admin/member).
  - All private data (tracked bets, bankroll, saved views, alerts) is scoped to an org and enforced by RLS — no cross-org leakage, verified by tests.
- **Technical notes:** see multi-tenancy in §4.

### F10 — Alerts / Notifications `P2`
> As **Alex**, I want to be notified when a bet above my EV threshold appears so that I don't miss fast-moving edges.
- **Acceptance criteria:** per-user alert rules (sport, market, min-EV); delivery via email/web push; opt-in only.
- **Technical notes:** `alert_rules` table; worker emits on new qualifying `ev_bets`.

### F11 — Responsible-Use & Compliance Surface `P0`
> As **the product**, I must present responsible-gambling messaging and jurisdiction disclaimers so that we operate ethically and legally.
- **Acceptance criteria:** persistent "decision support, not betting/financial advice" disclaimer; link to responsible-gambling resources; no auto-placing of bets anywhere in the product.
- **Technical notes:** static + footer; gate any future real-money integration behind legal review.

---

## 4. Database Schema

**Design principle — two layers:**
- **Shared market/model layer** (global, read-only to all authenticated users): `sports`, `events`, `players`, `odds_snapshots`, `model_runs`, `predictions`, `ev_bets`, `bet_results`. Same market data for everyone; written only by the service-role worker.
- **Private tenant layer** (isolated per organization via RLS): `organizations`, `memberships`, `tracked_bets`, `bankrolls`, `saved_views`, `alert_rules`. Every row carries `org_id`; RLS restricts access to members of that org.

### Entity-relationship overview
```
auth.users ──< memberships >── organizations
                                    │
        organizations ──< tracked_bets >── ev_bets ──> predictions ──> model_runs ──> sports
        organizations ──< bankrolls                    ev_bets ──> events ──> sports
        organizations ──< saved_views                  events ──< odds_snapshots
        organizations ──< alert_rules                  events ──< predictions
                                                        ev_bets ──< bet_results
```

### Shared layer (already in `supabase/migrations/0001_init.sql`, extended here)
| Table | Key fields | Notes |
|---|---|---|
| `sports` | `id text pk`, `name` | seed: golf, nfl, ncaab, ncaaf, soccer, nascar |
| `events` | `id uuid pk`, `sport_id fk`, `external_id`, `name`, `start_time`, `status` | unique `(sport_id, external_id)` |
| `players` | `id uuid pk`, `sport_id fk`, `name`, `external_ids jsonb` | unique `(sport_id, name)` |
| `odds_snapshots` | `id bigint identity pk`, `event_id fk`, `market`, `selection`, `book`, `price int`, `captured_at` | immutable time-series; partition by month at scale |
| `model_runs` | `id uuid pk`, `sport_id fk`, `model_version`, `trained_at`, `metrics jsonb` | store walk-forward AUC/MAE + CLV |
| `predictions` | `id uuid pk`, `model_run_id fk`, `event_id fk`, `market`, `selection`, `model_prob`, `novig_prob`, `ev`, `shap_top jsonb` | |
| `ev_bets` | `id uuid pk`, `prediction_id fk`, `sport_id fk`, `event_id fk`, `market`, `selection`, `book`, `price int`, `model_prob`, `novig_prob`, `ev`, `kelly_frac`, `rationale`, `flagged_at`, `status`, `trust_tier` | ranking surface; add `trust_tier text` = experimental\|trusted (CLV gate) |
| `bet_results` | `id uuid pk`, `ev_bet_id fk`, `closing_price int`, `clv double`, `settled_result`, `settled_at` | powers CLV |

### Private tenant layer (new — multi-tenancy)
```sql
create table organizations (
    id          uuid primary key default gen_random_uuid(),
    name        text not null,
    plan        text not null default 'free',        -- free | pro | team
    created_by  uuid not null references auth.users(id),
    created_at  timestamptz not null default now()
);

create type org_role as enum ('owner','admin','member');
create table memberships (
    org_id      uuid not null references organizations(id) on delete cascade,
    user_id     uuid not null references auth.users(id) on delete cascade,
    role        org_role not null default 'member',
    created_at  timestamptz not null default now(),
    primary key (org_id, user_id)
);

create table tracked_bets (
    id          uuid primary key default gen_random_uuid(),
    org_id      uuid not null references organizations(id) on delete cascade,
    user_id     uuid not null default auth.uid() references auth.users(id),
    ev_bet_id   uuid not null references ev_bets(id),
    book        text not null,
    price       integer not null,               -- price actually taken
    stake       numeric(12,2) not null check (stake >= 0),
    status      text not null default 'open',   -- open | settled | void
    result      text,                           -- win | loss | push | void
    closing_price integer,
    clv         double precision,
    placed_at   timestamptz not null default now(),
    settled_at  timestamptz
);

create table bankrolls (
    id          uuid primary key default gen_random_uuid(),
    org_id      uuid not null references organizations(id) on delete cascade,
    user_id     uuid not null default auth.uid() references auth.users(id),
    label       text not null default 'default',
    starting_units numeric(12,2) not null default 100,
    kelly_fraction numeric(4,3) not null default 0.25 check (kelly_fraction between 0 and 1),
    updated_at  timestamptz not null default now()
);

create table saved_views (
    id          uuid primary key default gen_random_uuid(),
    org_id      uuid not null references organizations(id) on delete cascade,
    user_id     uuid not null default auth.uid() references auth.users(id),
    name        text not null,
    sport       text,                           -- null = all
    market      text,
    min_ev      double precision not null default 0.02,
    shared      boolean not null default false, -- visible to whole org
    created_at  timestamptz not null default now()
);

create table alert_rules (
    id          uuid primary key default gen_random_uuid(),
    org_id      uuid not null references organizations(id) on delete cascade,
    user_id     uuid not null default auth.uid() references auth.users(id),
    sport       text,
    market      text,
    min_ev      double precision not null default 0.03,
    channel     text not null default 'email',  -- email | webpush
    enabled     boolean not null default true,
    created_at  timestamptz not null default now()
);
```

### Multi-tenancy enforcement (RLS)
A user may access a private row **iff** they are a member of that row's org. Reusable predicate:
```sql
-- helper: is the current user a member of :org_id ?
create or replace function is_org_member(o uuid) returns boolean
language sql stable security definer as $$
  select exists (select 1 from memberships m
                 where m.org_id = o and m.user_id = auth.uid());
$$;

alter table organizations enable row level security;
alter table memberships   enable row level security;
alter table tracked_bets  enable row level security;
alter table bankrolls     enable row level security;
alter table saved_views   enable row level security;
alter table alert_rules   enable row level security;

-- read/write private rows only within your orgs
create policy "member read tracked" on tracked_bets
    for select using (is_org_member(org_id));
create policy "member write tracked" on tracked_bets
    for all using (is_org_member(org_id)) with check (is_org_member(org_id));
-- (identical member policies for bankrolls, saved_views, alert_rules)

-- org visibility limited to orgs you belong to
create policy "see my orgs" on organizations
    for select using (is_org_member(id));
create policy "see my memberships" on memberships
    for select using (user_id = auth.uid() or is_org_member(org_id));
```
Shared-layer tables keep their public-read policies; they are org-agnostic and written only by the service role.

### Indexing strategy (common queries)
| Query | Index |
|---|---|
| Dashboard: open bets by sport, ranked by EV | `ev_bets (sport_id, status, ev desc, flagged_at desc)` |
| Odds lookup for an event/market over time | `odds_snapshots (event_id, market, selection, captured_at)` |
| Predictions for an event | `predictions (event_id, market)` |
| A user's tracked bets, recent first | `tracked_bets (org_id, user_id, placed_at desc)` |
| Membership checks (hot path for RLS) | `memberships (user_id, org_id)` and PK `(org_id, user_id)` |
| CLV rollups | `bet_results (ev_bet_id)`, `tracked_bets (org_id, status)` |
| Upcoming events | `events (sport_id, start_time)` |

### Data validation rules
- `price` is American odds, non-zero integer; `model_prob`/`novig_prob` ∈ (0,1); `ev` stored as fraction.
- `stake >= 0`; `kelly_fraction ∈ [0,1]`.
- `status`/`result` constrained to enumerated sets (enum or check).
- `odds_snapshots` are **append-only** (no updates/deletes) to preserve line history for CLV.
- Foreign keys enforce referential integrity; `on delete cascade` only within a tenant's own tree, never from shared→private.

---

## 5. API Specification

**Architecture.** Reads come primarily from **Supabase PostgREST** (auto-generated REST over the tables, guarded by RLS) via the client SDK. A **thin FastAPI service** covers actions that aren't a plain read. Auth is a Supabase JWT (Bearer) carrying `auth.uid()`; RLS does row-level authorization. Formats are JSON.

### Read endpoints (via Supabase PostgREST + client SDK)
| Endpoint | Auth | Purpose | Notes |
|---|---|---|---|
| `GET /rest/v1/ev_bets?status=eq.open&ev=gte.{x}&order=ev.desc` | anon or user JWT | Ranked dashboard rows | RLS: public read; filter by `sport_id`, `market` |
| `GET /rest/v1/predictions?event_id=eq.{id}` | anon/user | Prediction detail | |
| `GET /rest/v1/bet_results?...` | anon/user | CLV/aggregate inputs | |
| `GET /rest/v1/tracked_bets?...` | **user JWT** | A user's tracked bets | RLS: org member only |
| `GET /rest/v1/saved_views` / `alert_rules` / `bankrolls` | **user JWT** | Private config | RLS: org member only |

### Action endpoints (FastAPI)
| Endpoint | Method | Auth | Request → Response |
|---|---|---|---|
| `/api/v1/bets/track` | POST | user JWT | `{ ev_bet_id, org_id, book, price, stake }` → `201 { tracked_bet }` |
| `/api/v1/bets/{id}/settle` | POST | user JWT (org admin+) | `{ result, closing_price? }` → `200 { tracked_bet, clv }` |
| `/api/v1/clv/summary` | GET | user JWT | `?org_id&sport&window` → `{ n, beat_rate, mean_clv, roi }` |
| `/api/v1/orgs` | POST | user JWT | `{ name }` → `201 { org, membership(owner) }` |
| `/api/v1/orgs/{id}/invite` | POST | user JWT (admin+) | `{ email, role }` → `200 { membership }` |
| `/api/v1/admin/recompute` | POST | **service key** | `{ sport }` → `202` (trigger worker) |
| `/api/v1/health` | GET | none | `200 { status, version }` |

**Standard response envelope (errors):** `{ "error": { "code", "message", "details?" } }` with appropriate HTTP status (400 validation, 401 unauth, 403 RLS/role, 404, 429 rate-limited, 500).

### Authentication requirements
- **Public (anon key):** shared-layer reads only (dashboard works logged-out in read-only).
- **User JWT:** all private-layer reads/writes; org membership enforced by RLS + role checks for admin actions.
- **Service role:** worker writes to shared tables and `/admin/*`; **server-side only, never in the browser bundle.**

### Rate limiting
| Surface | Limit | Rationale |
|---|---|---|
| Public reads (anon) | 60 req/min/IP | Prevent scraping of the board |
| User reads | 300 req/min/user | Generous for interactive use |
| Action writes (track/settle) | 60 req/min/user | Abuse guard |
| `/admin/*` | service-key only, unmetered | Internal |
| **Upstream odds API** | governed by the worker's **credit budget**, not per-request limits | Credits ≠ requests; cache snapshots, never re-fetch a window |
- Enforce app limits at the edge (Vercel/Cloudflare) + FastAPI middleware; return `429` with `Retry-After`.

---

## 6. Non-Functional Requirements

### Performance
- Dashboard **First Contentful Paint < 1.5 s**, **interactive < 2.5 s** on a mid-range laptop / 4G.
- Dashboard query returns ≤ 200 ranked rows in **< 300 ms** server-side (indexed).
- Ingestion + model + EV run completes within its scheduled window (target **< 10 min** per sport per cycle).
- Data freshness: dashboard reflects the last completed ingestion cycle; show `flagged_at` age so users know staleness.

### Security
- All secrets from environment/`.env` (git-ignored); **service-role key server-side only**.
- **RLS default-deny** on every private table; cross-org isolation covered by automated tests.
- HTTPS everywhere; JWT verification on every authenticated request.
- No PII in URLs/query strings; least-privilege keys; rotate any exposed key.
- Supabase MCP (if used in dev) points at a **dev** project, never production data.
- Dependency scanning in CI; Sentry for runtime errors (no secrets in breadcrumbs).

### Accessibility (WCAG 2.1 AA)
- Full keyboard navigation of the table and filters; visible focus states.
- Color is **not** the only signal for +EV (icon/`+` sign + text, not just green).
- Contrast ≥ 4.5:1; semantic table markup; screen-reader labels on sortable headers and controls.
- Respect `prefers-reduced-motion` and `prefers-color-scheme`.

### Mobile responsiveness
- Web-first responsive layout is the cross-platform strategy (per tech-stack §1): usable on phones down to 360 px.
- Wide table scrolls horizontally inside its own container; page body never scrolls sideways.
- Touch targets ≥ 44 px; filters collapse into an accessible sheet on small screens.
- (React Native/Expo app is explicitly **v2** — see §7.)

### Reliability & Ops
- Idempotent ingestion; a failed cycle never corrupts prior data.
- Automated daily DB backups (+ periodic `pg_dump` to object storage on free tier); schema migrations in git via Supabase CLI.
- Alerting on failed worker runs.

### Compliance / Responsible use
- Persistent "**decision support, not betting or financial advice**" disclaimer; responsible-gambling resource link.
- **No auto-placing of bets** anywhere. Any future real-money feature is gated behind explicit legal/jurisdiction review.

---

## 7. Out of Scope

### Not in MVP
- **Automated/API bet placement.** Recommend only; a human always places the bet. (ToS + legal.)
- **More than golf as a *trusted* sport.** Others may appear as `experimental` but are not promoted until they clear the CLV gate.
- **Native mobile app** (React Native/Expo). Responsive web only for MVP.
- **Payments/subscriptions/billing.** No Stripe integration at launch (build after edge is proven).
- **Live/in-play betting**, arbitrage/middling finder, and multi-book auto line-shopping at scale.
- **User-uploaded custom models**; org-level custom model training.
- **Real-time (sub-minute) odds streaming.** MVP is scheduled batch refresh.
- **Social feed / public leaderboards.**

### Future considerations (v2+)
- Additional sports as each clears CLV (NFL/CBB sides are the *last*, least likely to yield edge).
- Expo/React Native app sharing a typed API client.
- Near-real-time odds polling + line-shopping across books.
- Subscription billing and org plan tiers.
- Alerting via push/Discord/Telegram; syndicate collaboration features.
- Cache/search stores (Upstash Redis, Postgres FTS) if hot paths demand them.

---

## 8. Success Metrics

**North-star metric:** **aggregate positive CLV of tracked bets.** Everything else is secondary — CLV is the only leading indicator that the product delivers real edge (viability §4). A product that grows users but shows non-positive CLV is failing at its core promise.

### Primary KPIs
| Metric | Definition |
|---|---|
| **Mean CLV / beat-rate** | Avg probability-point gain vs. close; % of tracked bets with positive CLV |
| **Model calibration** | Reliability-curve error on golf make-cut/top-N (out-of-sample) |
| **Activation** | % of signups who track ≥ 1 bet within 7 days |
| **Retention (WAU/MAU)** | Weekly and monthly active users |
| **Time-to-first-value** | Median time from login to first tracked/exported bet |
| **Referral rate** | % of active users who invite ≥ 1 person / create an org |

### Targets
| Horizon | Targets |
|---|---|
| **Launch week** | Golf CLV gate **passed** (documented positive mean CLV on backtest) before public bets are shown; ≥ 50 signups; ≥ 40% activation; dashboard p95 load < 2.5 s; zero cross-org data-leak incidents. |
| **Month 1** | ≥ 250 signups; **mean CLV of tracked bets > 0** across the cohort; ≥ 35% W1→W4 retention; ≥ 60% of actives use a filter/saved view; calibration error within target band. |
| **Month 3** | ≥ 1,000 users; **beat-rate ≥ 55%** on a ≥ 300-bet sample; ≥ 30% MAU stickiness; ≥ 1 additional sport promoted to `trusted` via CLV gate; NPS ≥ 40; infra cost within plan (odds API the dominant line item). |

### Guardrail metrics (must not regress)
- **De-vig correctness:** core math test suite stays 100% green on every deploy.
- **Cost:** hosting within budget; odds-API credit spend within the configured cap.
- **Trust integrity:** zero shipped bets whose "EV" was computed against a non-de-vigged baseline.
- **Responsible use:** disclaimer present on 100% of surfaces; no auto-placement code paths exist.

---

### Appendix — traceability to build
- Correctness core (F2/F4): `worker/core/devig.py`, `worker/core/clv.py` — implemented, 10 tests green.
- Dashboard (F5/F6): `web/app/page.tsx`, `web/lib/useEvBets.ts` — scaffolded, build green.
- Schema (§4): `supabase/migrations/0001_init.sql` (shared layer) + this PRD's tenant-layer DDL (to add as `0002_multitenancy.sql`).
- Open stubs before "real": `GolfModel._load_training_frame()`, `odds_api.fetch_odds()`, real SHAP in `_explain()`, CLV reporting in `fit()`.
