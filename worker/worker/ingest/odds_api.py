"""
Odds ingestion wrapper. Budget-aware by design (viability §4 / tech-stack §4):
The Odds API bills CREDITS, not requests — one /odds call costs markets x regions
credits, historical costs 10x. Cache snapshots and never re-fetch the same window.

The live path is intentionally guarded: it will not fire without ODDS_API_KEY in
the environment, and the orchestrator's --dry-run uses sample_market() instead so
you can exercise the whole pipeline without spending a credit or a rotated key.
"""
from __future__ import annotations

from ..config import CONFIG


def sample_market() -> dict:
    """A hand-built two-way market for --dry-run. No network, no credits."""
    return {
        "event": {"sport_id": "golf", "external_id": "sample-open-2026",
                  "name": "Sample Open 2026", "start_time": "2026-07-24T12:00:00Z"},
        "market": "make_cut",
        "selections": [
            # (player, our_model_prob, offered_price, other_side_price)
            {"name": "Player A", "model_prob": 0.62, "price": -110, "other_price": -110},
            {"name": "Player B", "model_prob": 0.55, "price": +120, "other_price": -140},
            {"name": "Player C", "model_prob": 0.48, "price": +180, "other_price": -220},
            {"name": "Player D", "model_prob": 0.71, "price": -160, "other_price": +135},
        ],
    }


def fetch_odds(sport_key: str, markets: str, regions: str = "us") -> dict:
    """
    Live fetch. Requires ODDS_API_KEY. Raises loudly if unconfigured rather than
    silently returning nothing. Implement the actual HTTP + snapshot-caching here.
    """
    if not CONFIG.odds_api_key:
        raise RuntimeError(
            "ODDS_API_KEY is not set. Fill .env (and rotate any shared key), or "
            "run the worker with --dry-run to use sample data instead."
        )
    # Deliberately not implemented against a live key in this scaffold. Sketch:
    #   import httpx
    #   url = f"{CONFIG.odds_api_base}/sports/{sport_key}/odds"
    #   params = {"apiKey": CONFIG.odds_api_key, "regions": regions,
    #             "markets": markets, "oddsFormat": "american"}
    #   resp = httpx.get(url, params=params, timeout=30); resp.raise_for_status()
    #   ... persist raw response to odds_snapshots, then normalize ...
    raise NotImplementedError(
        "Live odds fetch not wired in the scaffold. Add the httpx call above, "
        "persist to odds_snapshots, and mind the credit accounting."
    )
