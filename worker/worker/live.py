"""
Live +EV worker: fetch live odds -> no-vig consensus -> flag +EV -> write to Supabase.

    python -m worker.live --all --write            # all sports -> Supabase (daily job)
    python -m worker.live --sport mlb --dry-run     # sample odds, no key/DB
    python -m worker.live --all                      # all sports, print only (no write)

Sports searched by --all: MLB (h2h), Golf (outrights), NASCAR (outrights),
Soccer (h2h/1X2), NFL (h2h) — whichever are in season on the odds API.

Needs, for the live path:
  ODDS_API_KEY   free key from https://the-odds-api.com   (in .env / CI secret)
  DATABASE_URL   Supabase connection string (--write only) (in .env / CI secret)
"""
from __future__ import annotations

import argparse

from .config import CONFIG
from .core.positive_ev import compute_event_bets, rationale_for
from .ingest.odds_api import fetch_all, fetch_live, sample_live_events

SPORT_LABEL = {"mlb": "MLB", "golf": "Golf", "nascar": "NASCAR",
               "soccer": "Soccer", "nfl": "NFL", "soccer_epl": "Premier League"}


# A real line-shopping edge is small. Anything huge is a stale/error line you
# can't actually bet, or a de-vig artifact — not a bet we should surface.
EV_MAX = 0.20
# Outright (golf/NASCAR winner) markets are noisy: tiny-prob longshots trivially
# clear any EV bar via favorite-longshot bias. Only consider realistic contenders.
OUTRIGHT_FAIR_FLOOR = 0.03
OUTRIGHT_MAX_PRICE = 3000  # skip anything longer than +3000 (30-1)


def _bets_for(events: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for ev in events:
        market = ev["market"]
        for b in compute_event_bets(ev, CONFIG.min_ev, CONFIG.kelly_fraction):
            if b["ev"] > EV_MAX:
                continue  # artifact / unbettable stale line
            if market == "outright" and (
                b["model_prob"] < OUTRIGHT_FAIR_FLOOR or b["price"] > OUTRIGHT_MAX_PRICE
            ):
                continue  # longshot noise, not a real outright edge
            b["sport_id"] = ev["sport_id"]
            b["market"] = market
            b["event"] = ev
            b["rationale"] = rationale_for(b, market)
            rows.append(b)
    rows.sort(key=lambda r: r["ev"], reverse=True)
    return rows


def _print(rows: list[dict]) -> None:
    print(f"\n  {'Sel':<26}{'Sport':<8}{'Book':<12}{'Price':>7}{'Fair':>7}{'EV':>8}")
    print("  " + "-" * 68)
    for r in rows[:50]:
        print(f"  {r['selection'][:25]:<26}{r['sport_id']:<8}{r['book'][:11]:<12}"
              f"{r['price']:>+7}{r['model_prob']*100:>6.1f}%{r['ev']*100:>+7.1f}%")


def run(sport: str, dry_run: bool, write: bool, regions: str, all_sports: bool) -> None:
    if dry_run:
        events = sample_live_events()
    elif all_sports:
        events = fetch_all(regions)
    else:
        events = fetch_live(sport, regions)

    rows = _bets_for(events)
    fetched = sorted({e["sport_id"] for e in events})
    print(f"\n  {len(rows)} +EV bets >= {CONFIG.min_ev*100:.1f}% across {len(events)} events "
          f"in {len(fetched)} sport(s): {', '.join(fetched) or '-'} "
          f"({'sample' if dry_run else 'live'}).")
    _print(rows)

    if dry_run or not write:
        print("\n  [no write] Run with --write (and DATABASE_URL set) to publish to Supabase.")
        return

    from .db import Db
    db = Db()
    # Refresh only the sports we actually pulled odds for (leaves others untouched).
    for sp in fetched:
        db.ensure_sport(sp, SPORT_LABEL.get(sp, sp.title()))
        db.clear_open(sp)

    written = 0
    for r in rows:
        ev = r.pop("event")
        r["event_id"] = db.upsert_event(ev["sport_id"], ev["external_id"],
                                        ev["name"], ev.get("start_time"))
        r["prediction_id"] = None
        r["status"] = "open"
        written += db.insert_ev_bets([r])
    print(f"\n  Wrote {written} live +EV bets across {len(fetched)} sport(s). "
          f"Refresh the dashboard.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Live +EV worker")
    ap.add_argument("--sport", default="mlb", help="single sport (with --sport mode)")
    ap.add_argument("--all", action="store_true", dest="all_sports",
                    help="search all target sports (mlb, golf, nascar, soccer, nfl)")
    ap.add_argument("--dry-run", action="store_true",
                    help="use sample odds; print; no key/DB needed")
    ap.add_argument("--write", action="store_true",
                    help="write results to Supabase (needs ODDS_API_KEY + DATABASE_URL)")
    ap.add_argument("--regions", default="us",
                    help="comma-separated odds regions, e.g. us,us2,eu (more books = more credits)")
    args = ap.parse_args()
    run(args.sport, args.dry_run, args.write, args.regions, args.all_sports)


if __name__ == "__main__":
    main()
