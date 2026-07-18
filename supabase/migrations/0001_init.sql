-- 0001_init.sql — core schema for the +EV platform.
-- Relational by design (see research/tech-stack.md §3). Public model outputs are
-- world-readable; user-scoped rows are locked to auth.uid() via RLS.

create extension if not exists "pgcrypto";

-- ------------------------------------------------------------------ reference
create table sports (
    id          text primary key,          -- 'golf', 'nfl', 'ncaab', ...
    name        text not null,
    created_at  timestamptz not null default now()
);

create table events (
    id          uuid primary key default gen_random_uuid(),
    sport_id    text not null references sports(id),
    external_id text,                        -- id from the odds/stats provider
    name        text not null,
    start_time  timestamptz not null,
    status      text not null default 'scheduled',  -- scheduled | live | final
    created_at  timestamptz not null default now(),
    unique (sport_id, external_id)
);
create index on events (sport_id, start_time);

create table players (
    id          uuid primary key default gen_random_uuid(),
    sport_id    text not null references sports(id),
    name        text not null,
    external_ids jsonb not null default '{}'::jsonb,
    unique (sport_id, name)
);

-- ------------------------------------------------------------ odds time-series
-- Grows fast. Postgres is fine at MVP; partition by month when volume demands.
create table odds_snapshots (
    id          bigint generated always as identity primary key,
    event_id    uuid not null references events(id) on delete cascade,
    market      text not null,               -- 'make_cut','top_10','moneyline','spread',...
    selection   text not null,               -- player name / team / side
    book        text not null,               -- 'pinnacle','draftkings',...
    price       integer not null,            -- American odds (e.g. -110, +240)
    captured_at timestamptz not null default now()
);
create index on odds_snapshots (event_id, market, selection, captured_at);

-- ----------------------------------------------------------------- model runs
create table model_runs (
    id            uuid primary key default gen_random_uuid(),
    sport_id      text not null references sports(id),
    model_version text not null,
    trained_at    timestamptz not null default now(),
    metrics       jsonb not null default '{}'::jsonb   -- walk-forward AUC/MAE/CLV, etc.
);

-- Model probability for a selection, alongside the market's no-vig fair prob.
create table predictions (
    id            uuid primary key default gen_random_uuid(),
    model_run_id  uuid not null references model_runs(id) on delete cascade,
    event_id      uuid not null references events(id) on delete cascade,
    market        text not null,
    selection     text not null,
    model_prob    double precision not null,     -- our estimate
    novig_prob    double precision,              -- de-vigged sharp-market fair prob
    ev            double precision,              -- expected value at the offered price
    shap_top      jsonb not null default '[]'::jsonb,  -- [{feature, value}] top drivers
    created_at    timestamptz not null default now()
);
create index on predictions (event_id, market);

-- What the dashboard ranks: a flagged +EV bet at a specific book/price.
create table ev_bets (
    id            uuid primary key default gen_random_uuid(),
    prediction_id uuid not null references predictions(id) on delete cascade,
    sport_id      text not null references sports(id),
    event_id      uuid not null references events(id) on delete cascade,
    market        text not null,
    selection     text not null,
    book          text not null,
    price         integer not null,          -- American odds offered
    model_prob    double precision not null,
    novig_prob    double precision,
    ev            double precision not null, -- ranking key (fraction, e.g. 0.043 = +4.3%)
    kelly_frac    double precision,          -- fractional-Kelly stake suggestion
    rationale     text,                      -- 1-2 sentence explanation (SHAP-derived)
    flagged_at    timestamptz not null default now(),
    status        text not null default 'open'  -- open | closed | settled
);
create index on ev_bets (sport_id, ev desc, flagged_at desc);

-- CLV / performance tracking — the honest scoreboard.
create table bet_results (
    id            uuid primary key default gen_random_uuid(),
    ev_bet_id     uuid not null references ev_bets(id) on delete cascade,
    closing_price integer,                   -- American odds at close
    clv           double precision,          -- closing-line value (prob points gained)
    settled_result text,                     -- win | loss | push | void
    settled_at    timestamptz
);

-- User-scoped: a user's tracked/placed bets. RLS locks to the owner.
create table user_bets (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null default auth.uid() references auth.users(id) on delete cascade,
    ev_bet_id   uuid not null references ev_bets(id) on delete cascade,
    stake       numeric(12,2),
    placed_at   timestamptz not null default now()
);
create index on user_bets (user_id, placed_at desc);

-- ------------------------------------------------------------------------ RLS
-- Public model output: readable by anyone (incl. anon), writable only by the
-- service role (the worker), which bypasses RLS. Default-deny everywhere else.
-- CRITICAL: enable RLS on EVERY table. In Supabase the anon/authenticated roles
-- hold default table grants, so RLS-disabled = wide-open write/delete via PostgREST.
-- "No policy" only means "no access" when RLS is ENABLED. Enabling with no policy
-- => default-deny (service role still bypasses RLS and can read/write).
alter table sports          enable row level security;
alter table events          enable row level security;
alter table players         enable row level security;
alter table odds_snapshots  enable row level security;
alter table model_runs      enable row level security;
alter table predictions     enable row level security;
alter table ev_bets         enable row level security;
alter table bet_results     enable row level security;
alter table user_bets       enable row level security;

-- Public read on the world-facing model output; writes are service-role-only
-- (the worker bypasses RLS). players is dimension data safe to expose.
create policy "public read sports"       on sports       for select using (true);
create policy "public read events"        on events       for select using (true);
create policy "public read players"       on players      for select using (true);
create policy "public read predictions"   on predictions  for select using (true);
create policy "public read ev_bets"       on ev_bets      for select using (true);
create policy "public read bet_results"   on bet_results  for select using (true);

-- odds_snapshots and model_runs are INTERNAL: RLS enabled + NO policy => default-
-- deny to anon/authenticated. Only the service-role worker (bypasses RLS) touches
-- them. This is now enforced (RLS is on), not merely asserted by a comment.

-- user_bets: each user sees and edits ONLY their own rows.
create policy "own bets read"   on user_bets for select using (auth.uid() = user_id);
create policy "own bets insert" on user_bets for insert with check (auth.uid() = user_id);
create policy "own bets update" on user_bets for update using (auth.uid() = user_id);
create policy "own bets delete" on user_bets for delete using (auth.uid() = user_id);

insert into sports (id, name) values
    ('golf','Golf'), ('nfl','NFL'), ('ncaab','NCAA Basketball'),
    ('ncaaf','NCAA Football'), ('soccer','Soccer'), ('nascar','NASCAR')
on conflict do nothing;
