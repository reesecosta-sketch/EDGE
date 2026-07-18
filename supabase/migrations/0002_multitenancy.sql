-- 0002_multitenancy.sql — private tenant layer (PRD §4).
-- Adds the org-scoped layer on top of 0001's shared market/model layer.
-- Shared tables (sports/events/odds/predictions/ev_bets/bet_results) stay global,
-- readable by all, written only by the service role. Everything here is private
-- and isolated per organization via RLS.
--
-- NOTE: 0001 created a placeholder `user_bets` (per-user, no org). It is superseded
-- by `tracked_bets` (org-scoped) below. It is left in place intentionally — dropping
-- it is a destructive change that must be reviewed/escalated, so a later migration
-- can remove it once nothing references it.

-- ------------------------------------------------------------ trust tier on bets
-- A sport/bet is only shown as "trusted" once it clears the CLV gate (roadmap M1).
alter table ev_bets
    add column if not exists trust_tier text not null default 'experimental'
    check (trust_tier in ('experimental', 'trusted'));

-- ------------------------------------------------------------------ organizations
create table organizations (
    id          uuid primary key default gen_random_uuid(),
    name        text not null,
    plan        text not null default 'free',        -- free | pro | team
    created_by  uuid not null references auth.users(id),
    created_at  timestamptz not null default now()
);

create type org_role as enum ('owner', 'admin', 'member');

create table memberships (
    org_id      uuid not null references organizations(id) on delete cascade,
    user_id     uuid not null references auth.users(id) on delete cascade,
    role        org_role not null default 'member',
    created_at  timestamptz not null default now(),
    primary key (org_id, user_id)
);
-- Hot path for RLS membership checks.
create index on memberships (user_id, org_id);

-- ------------------------------------------------------------------ private tables
create table tracked_bets (
    id            uuid primary key default gen_random_uuid(),
    org_id        uuid not null references organizations(id) on delete cascade,
    user_id       uuid not null default auth.uid() references auth.users(id),
    ev_bet_id     uuid not null references ev_bets(id),
    book          text not null,
    price         integer not null,               -- price actually taken (American)
    stake         numeric(12,2) not null check (stake >= 0),
    status        text not null default 'open',   -- open | settled | void
    result        text,                           -- win | loss | push | void
    closing_price integer,
    clv           double precision,
    placed_at     timestamptz not null default now(),
    settled_at    timestamptz
);
create index on tracked_bets (org_id, user_id, placed_at desc);
create index on tracked_bets (org_id, status);

create table bankrolls (
    id             uuid primary key default gen_random_uuid(),
    org_id         uuid not null references organizations(id) on delete cascade,
    user_id        uuid not null default auth.uid() references auth.users(id),
    label          text not null default 'default',
    starting_units numeric(12,2) not null default 100,
    kelly_fraction numeric(4,3) not null default 0.25
                   check (kelly_fraction between 0 and 1),
    updated_at     timestamptz not null default now()
);

create table saved_views (
    id          uuid primary key default gen_random_uuid(),
    org_id      uuid not null references organizations(id) on delete cascade,
    user_id     uuid not null default auth.uid() references auth.users(id),
    name        text not null,
    sport       text,                             -- null = all
    market      text,
    min_ev      double precision not null default 0.02,
    shared      boolean not null default false,   -- visible to whole org
    created_at  timestamptz not null default now()
);

create table alert_rules (
    id          uuid primary key default gen_random_uuid(),
    org_id      uuid not null references organizations(id) on delete cascade,
    user_id     uuid not null default auth.uid() references auth.users(id),
    sport       text,
    market      text,
    min_ev      double precision not null default 0.03,
    channel     text not null default 'email',    -- email | webpush
    enabled     boolean not null default true,
    created_at  timestamptz not null default now()
);

-- --------------------------------------------------------------- membership helper
-- SECURITY DEFINER so the RLS predicate can read memberships without recursing into
-- memberships' own RLS. Returns true iff the current user belongs to org o.
create or replace function is_org_member(o uuid) returns boolean
language sql stable security definer
set search_path = public as $$
    select exists (
        select 1 from memberships m
        where m.org_id = o and m.user_id = auth.uid()
    );
$$;

-- ------------------------------------------------------------------------ RLS
alter table organizations enable row level security;
alter table memberships   enable row level security;
alter table tracked_bets  enable row level security;
alter table bankrolls     enable row level security;
alter table saved_views   enable row level security;
alter table alert_rules   enable row level security;

-- Org visibility limited to orgs you belong to.
create policy "see my orgs" on organizations
    for select using (is_org_member(id));
create policy "creator inserts org" on organizations
    for insert with check (auth.uid() = created_by);

create policy "see my memberships" on memberships
    for select using (user_id = auth.uid() or is_org_member(org_id));

-- Private data: read/write only within your orgs. Default-deny is the baseline;
-- these are the only grants. (No policy => no anon/other-user access.)
create policy "member all tracked_bets" on tracked_bets
    for all using (is_org_member(org_id)) with check (is_org_member(org_id));
create policy "member all bankrolls" on bankrolls
    for all using (is_org_member(org_id)) with check (is_org_member(org_id));
create policy "member all saved_views" on saved_views
    for all using (is_org_member(org_id)) with check (is_org_member(org_id));
create policy "member all alert_rules" on alert_rules
    for all using (is_org_member(org_id)) with check (is_org_member(org_id));

-- --------------------------------------------------- auto-create a personal org
-- On signup, give each new user a personal org and an owner membership so the app
-- always has a tenant to scope private rows to (MVP: one personal org per user;
-- syndicate/invite UX is deferred — roadmap §1).
create or replace function handle_new_user() returns trigger
language plpgsql security definer
set search_path = public as $$
declare
    new_org uuid;
begin
    insert into organizations (name, created_by)
        values (coalesce(new.email, 'My') || '''s workspace', new.id)
        returning id into new_org;
    insert into memberships (org_id, user_id, role)
        values (new_org, new.id, 'owner');
    return new;
end;
$$;

create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function handle_new_user();
