-- 0003_live_ev.sql — support model-free live +EV (line-shopping) bets.
-- Run in the Supabase SQL Editor after 0001 (and 0002 if applied).
--
-- Line-shopping bets are flagged from live odds vs. the no-vig market consensus;
-- they have no model prediction, so prediction_id must be nullable.

alter table ev_bets alter column prediction_id drop not null;

-- Register the sports the live feed can cover.
insert into sports (id, name) values
    ('mlb', 'MLB'),
    ('soccer_epl', 'Premier League'),
    ('tennis', 'Tennis')
on conflict do nothing;
