"""
Live +EV worker: fetch live odds -> no-vig consensus -> flag +EV -> write to Supabase.

    python -m worker.live --sport mlb --dry-run      # sample odds, prints table, no key/DB
    python -m worker.live --sport mlb --write        # real odds -> Supabase (needs keys)
    python -m worker.live --sport mlb                # real odds, print only (no write)

Needs, for the live path:
  ODDS_API_KEY   free key from https://the-odds-api.com   (in .env)
  DATABASE_URL   Supabase connection string (--write only) (in .env, server-side)
"""
from __future__ import annotations

import argparse

from .config import CONFIG
from .core.positive_ev import compute_event_bets, rationale_for
from .ingest.odds_api import fetch_live, sample_live_events

SPORT_LABEL = {"mlb": "MLB", "soccer_epl": "Premier League", "nfl": "NFL"}


def _bets_for(events: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for ev in events:
        for b in compute_event_bets(ev, CONFIG.min_ev, CONFIG.kelly_fraction):
            b["sport_id"] = ev["sport_id"]
            b["market"] = ev["market"]
            b["event"] = ev  # keep for event upsert
            b["rationale"] = rationale_for(b, ev["market"])
            rows.append(b)
    rows.sort(key=lambda r: r["ev"], reverse=True)
    return rows


def _print(rows: list[dict]) -> None:
    print(f"\n  {'Sel':<26}{'Book':<12}{'Price':>7}{'Fair':>7}{'EV':>8}{'Kelly':>8}")
    print("  " + "-" * 68)
    for r in rows[:40]:
        print(f"  {r['selection'][:25]:<26}{r['book'][:11]:<12}{r['price']:>+7}"
              f"{r['model_prob']*100:>6.1f}%{r['ev']*100:>+7.1f}%{r['kelly_frac']*100:>7.2f}%")
    print()
    for r in rows[:10]:
        print(f"  - {r['rationale']}")


def run(sport: str, dry_run: bool, write: bool, regions: str = "us") -> None:
    events = sample_live_events() if dry_run else fetch_live(sport, regions)
    if dry_run:
        events = [e for e in events if e["sport_id"] == sport] or events
    rows = _bets_for(events)
    print(f"\n  {SPORT_LABEL.get(sport, sport)}: {len(rows)} +EV bets "
          f">= {CONFIG.min_ev*100:.1f}% across {len(events)} events "
          f"(consensus de-vig, {'sample' if dry_run else 'live'}).")
    _print(rows)

    if dry_run or not write:
        print("\n  [no write] Run with --write (and DATABASE_URL set) to publish to Supabase.")
        return

    from .db import Db
    db = Db()
    db.ensure_sport(sport, SPORT_LABEL.get(sport, sport))
    removed = db.clear_open(sport)
    written = 0
    for r in rows:
        ev = r.pop("event")
        event_id = db.upsert_event(ev["sport_id"], ev["external_id"], ev["name"],
                                   ev.get("start_time"))
        r["event_id"] = event_id
        r["prediction_id"] = None
        r["status"] = "open"
        written += db.insert_ev_bets([r])
    print(f"\n  Wrote {written} live +EV bets to Supabase (cleared {removed} stale). "
          f"Refresh the dashboard.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Live +EV worker")
    ap.add_argument("--sport", default="mlb", choices=list(SPORT_LABEL))
    ap.add_argument("--dry-run", action="store_true",
                    help="use sample odds; print; no key/DB needed")
    ap.add_argument("--write", action="store_true",
                    help="write results to Supabase (needs ODDS_API_KEY + DATABASE_URL)")
    ap.add_argument("--regions", default="us",
                    help="comma-separated odds regions, e.g. us,us2,eu (more books = more credits)")
    args = ap.parse_args()
    run(args.sport, args.dry_run, args.write, args.regions)


if __name__ == "__main__":
    main()
