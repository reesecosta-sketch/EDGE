-- EDGE demo seed — makes the dashboard show live, database-backed bets.
-- Run this in the Supabase SQL Editor AFTER 0001_init.sql has been run.
-- (0002_multitenancy.sql is optional and not needed for the dashboard.)
--
-- Idempotent: re-running replaces the demo rows. Inserts the FK chain the schema
-- requires (event -> model_run -> predictions -> ev_bets). The dashboard reads
-- ev_bets via the public-read RLS policy, so the publishable key can see these.

begin;

-- clear any previous demo data
delete from ev_bets    where event_id in (select id from events where external_id = 'demo-open-2026');
delete from predictions where event_id in (select id from events where external_id = 'demo-open-2026');
delete from events     where external_id = 'demo-open-2026';

with e as (
  insert into events (sport_id, external_id, name, start_time, status)
  values ('golf', 'demo-open-2026', 'The Open Championship', now() + interval '2 days', 'scheduled')
  returning id
),
m as (
  insert into model_runs (sport_id, model_version, metrics)
  values ('golf', 'demo-seed-0.1', '{"note":"demo seed"}'::jsonb)
  returning id
),
bets(selection, market, book, price, model_prob, novig_prob, ev, kelly_frac, rationale) as (
  values
    ('Ludvig Åberg',     'top_10',   'pinnacle',   275,  0.32, 0.243, 0.198, 0.045, 'Model gives Åberg a 32% top-10 chance vs. 24% fair — a +7.7pt edge from strokes-gained approach and links course fit.'),
    ('Tommy Fleetwood',  'make_cut', 'draftkings', -140, 0.71, 0.612, 0.156, 0.050, '71% make-cut vs. 61% fair — a +9.8pt edge from elite driving accuracy and strong recent form.'),
    ('Viktor Hovland',   'top_5',    'fanduel',    650,  0.16, 0.121, 0.174, 0.019, '16% top-5 vs. 12% fair — a +3.9pt edge; iron play and course history carry the projection.'),
    ('Robert MacIntyre', 'make_cut', 'betmgm',     120,  0.55, 0.461, 0.210, 0.038, '55% make-cut vs. 46% fair — a +8.9pt edge; home-nation links pedigree and a putting uptick.'),
    ('Matt Fitzpatrick', 'top_20',   'pinnacle',   180,  0.44, 0.368, 0.232, 0.050, '44% top-20 vs. 37% fair — a +7.2pt edge from scrambling and wind-scoring history.'),
    ('Xander Schauffele','outright', 'caesars',    1400, 0.09, 0.071, 0.286, 0.010, '9% to win vs. 7% fair — a +1.9pt edge; consistency and closing record priced softly.'),
    ('Aaron Rai',        'top_10',   'draftkings', 450,  0.21, 0.171, 0.155, 0.018, '21% top-10 vs. 17% fair — a +3.9pt edge; accuracy fits a demanding setup.'),
    ('Shane Lowry',      'make_cut', 'pinnacle',   105,  0.58, 0.508, 0.189, 0.041, '58% make-cut vs. 51% fair — a +7.2pt edge; elite bad-weather scoring and course comfort.')
),
p as (
  insert into predictions (model_run_id, event_id, market, selection, model_prob, novig_prob, ev, shap_top)
  select m.id, e.id, b.market, b.selection, b.model_prob, b.novig_prob, b.ev, '[]'::jsonb
  from e, m, bets b
  returning id, event_id, selection
)
insert into ev_bets (prediction_id, sport_id, event_id, market, selection, book, price,
                     model_prob, novig_prob, ev, kelly_frac, rationale, status)
select p.id, 'golf', p.event_id, b.market, b.selection, b.book, b.price,
       b.model_prob, b.novig_prob, b.ev, b.kelly_frac, b.rationale, 'open'
from p
join bets b on b.selection = p.selection;

commit;

-- Sanity check (optional): select count(*) from ev_bets where status = 'open';
