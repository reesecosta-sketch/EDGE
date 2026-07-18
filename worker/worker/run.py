"""
Orchestrator: ingest odds -> devig -> EV -> Kelly -> rationale -> rank -> (write).

    python -m worker.run --sport golf --dry-run     # sample odds, prints table, no DB
    python -m worker.run --sport golf               # live path (needs .env keys + DB)

--dry-run exercises the entire core math path (the part that must be correct)
without a key, a credit, or a database. That's the fast feedback loop.
"""
from __future__ import annotations

import argparse

from .config import CONFIG
from .core.devig import expected_value, kelly_fraction, remove_vig
from .core.rationale import build_rationale
from .ingest.odds_api import sample_market


def _fair_probs(sels: list[dict], method: str) -> list[float]:
    """
    De-vig correctly for the market TYPE. This distinction is a common, expensive
    error (viability §1):
      - Independent props (each selection has its own opposite price, e.g. a
        player's make-cut vs miss-cut): de-vig EACH selection against its own
        other side. Players making the cut are NOT mutually exclusive.
      - Mutually-exclusive market (moneyline, N-way outright winner): de-vig all
        selections together so the fair probs sum to 1.
    """
    if all("other_price" in s for s in sels):
        return [remove_vig([s["price"], s["other_price"]], method)[0] for s in sels]
    return remove_vig([s["price"] for s in sels], method=method)


def evaluate_market(market: dict, min_ev: float, method: str) -> list[dict]:
    """Compute no-vig fair prob, EV, and Kelly for every selection in a market."""
    sels = market["selections"]
    fair = _fair_probs(sels, method)

    bets = []
    for s, novig in zip(sels, fair):
        ev = expected_value(s["model_prob"], s["price"])
        bets.append({
            "selection": s["name"],
            "market": market["market"],
            "price": s["price"],
            "model_prob": s["model_prob"],
            "novig_prob": novig,
            "ev": ev,
            "kelly_frac": kelly_fraction(s["model_prob"], s["price"],
                                         CONFIG.kelly_fraction),
            "rationale": build_rationale(s["name"], market["market"],
                                         s["model_prob"], novig,
                                         s.get("shap_top", [])),
        })
    bets = [b for b in bets if b["ev"] >= min_ev]
    bets.sort(key=lambda b: b["ev"], reverse=True)
    return bets


def _print_table(event: dict, bets: list[dict]) -> None:
    print(f"\n  {event['name']}  ({event['sport_id']})")
    print(f"  {'Sel':<12}{'Mkt':<10}{'Price':>7}{'Model':>8}{'Fair':>8}"
          f"{'EV':>8}{'Kelly':>8}")
    print("  " + "-" * 61)
    for b in bets:
        print(f"  {b['selection']:<12}{b['market']:<10}{b['price']:>+7}"
              f"{b['model_prob']*100:>7.1f}%{b['novig_prob']*100:>7.1f}%"
              f"{b['ev']*100:>+7.1f}%{b['kelly_frac']*100:>7.2f}%")
    print()
    for b in bets:
        print(f"  - {b['rationale']}")


def run(sport: str, dry_run: bool) -> None:
    if dry_run:
        market = sample_market()
        bets = evaluate_market(market, CONFIG.min_ev, CONFIG.devig_method)
        _print_table(market["event"], bets)
        print(f"\n  [dry-run] {len(bets)} +EV bets >= {CONFIG.min_ev*100:.1f}% "
              f"(devig={CONFIG.devig_method}). Nothing written.")
        return

    # Live path: fetch odds, run the sport model, write ev_bets. Wired to fail
    # clearly until the model's data hook and the odds fetch are connected.
    from .ingest.odds_api import fetch_odds  # noqa: F401
    raise SystemExit(
        "Live path needs: (1) GolfModel._load_training_frame() connected to real "
        "features, (2) odds_api.fetch_odds() implemented, (3) DATABASE_URL set. "
        "Use --dry-run meanwhile."
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="+EV worker")
    ap.add_argument("--sport", default="golf")
    ap.add_argument("--dry-run", action="store_true",
                    help="use sample odds; print ranked table; write nothing")
    args = ap.parse_args()
    run(args.sport, args.dry_run)


if __name__ == "__main__":
    main()
