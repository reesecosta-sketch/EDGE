"""
Odds ingestion — The Odds API (https://the-odds-api.com).

Budget-aware by design: the API bills CREDITS (roughly markets x regions per call),
so one /odds call for one sport+market+region is ~1 credit. Cache/limit accordingly.

- sample_market()      : two-way golf props for run.py --dry-run (no network).
- sample_live_events() : sample MLB moneyline board for live.py --dry-run (no key).
- fetch_live()         : real call; requires ODDS_API_KEY. Returns normalized events.
"""
from __future__ import annotations

from ..config import CONFIG

# The Odds API sport keys -> our internal sport_id + display market name.
SPORT_KEYS = {
    "mlb": ("baseball_mlb", "moneyline", "h2h"),
    "soccer_epl": ("soccer_epl", "moneyline", "h2h"),
    "nfl": ("americanfootball_nfl", "moneyline", "h2h"),
}


def sample_market() -> dict:
    """Two-way golf make-cut props for run.py --dry-run."""
    return {
        "event": {"sport_id": "golf", "external_id": "sample-open-2026",
                  "name": "Sample Open 2026", "start_time": "2026-07-24T12:00:00Z"},
        "market": "make_cut",
        "selections": [
            {"name": "Player A", "model_prob": 0.62, "price": -110, "other_price": -110},
            {"name": "Player B", "model_prob": 0.55, "price": +120, "other_price": -140},
            {"name": "Player C", "model_prob": 0.48, "price": +180, "other_price": -220},
            {"name": "Player D", "model_prob": 0.71, "price": -160, "other_price": +135},
        ],
    }


def sample_live_events() -> list[dict]:
    """Normalized sample MLB moneyline board (no key) for live.py --dry-run.
    One book is deliberately off-market to produce a +EV flag."""
    return [
        {
            "external_id": "sample-nyy-bos",
            "sport_id": "mlb",
            "name": "Boston Red Sox @ New York Yankees",
            "start_time": "2026-07-19T23:05:00Z",
            "market": "moneyline",
            "books": [
                {"book": "pinnacle",   "prices": {"New York Yankees": -145, "Boston Red Sox": +133}},
                {"book": "draftkings", "prices": {"New York Yankees": -150, "Boston Red Sox": +130}},
                {"book": "fanduel",    "prices": {"New York Yankees": -155, "Boston Red Sox": +136}},
                {"book": "betmgm",     "prices": {"New York Yankees": -148, "Boston Red Sox": +155}},  # soft: Sox price too high
            ],
        },
        {
            "external_id": "sample-lad-sf",
            "sport_id": "mlb",
            "name": "San Francisco Giants @ Los Angeles Dodgers",
            "start_time": "2026-07-19T02:10:00Z",
            "market": "moneyline",
            "books": [
                {"book": "pinnacle",   "prices": {"Los Angeles Dodgers": -170, "San Francisco Giants": +156}},
                {"book": "draftkings", "prices": {"Los Angeles Dodgers": -175, "San Francisco Giants": +150}},
                {"book": "caesars",    "prices": {"Los Angeles Dodgers": -160, "San Francisco Giants": +150}},  # soft: Dodgers cheap
            ],
        },
    ]


def fetch_live(sport: str, regions: str = "us") -> list[dict]:
    """
    Real fetch from The Odds API. Requires ODDS_API_KEY. Returns normalized events
    in the same shape as sample_live_events(). Logs remaining credit balance.
    """
    if sport not in SPORT_KEYS:
        raise ValueError(f"Unsupported sport '{sport}'. Options: {list(SPORT_KEYS)}")
    if not CONFIG.odds_api_key:
        raise RuntimeError(
            "ODDS_API_KEY is not set. Get a free key at https://the-odds-api.com, "
            "put it in .env, or run with --dry-run to use sample data."
        )
    import httpx

    sport_key, market_name, market_key = SPORT_KEYS[sport]
    url = f"{CONFIG.odds_api_base}/sports/{sport_key}/odds"
    params = {
        "apiKey": CONFIG.odds_api_key,
        "regions": regions,
        "markets": market_key,
        "oddsFormat": "american",
        "dateFormat": "iso",
    }
    resp = httpx.get(url, params=params, timeout=30)
    resp.raise_for_status()
    remaining = resp.headers.get("x-requests-remaining")
    used = resp.headers.get("x-requests-used")
    print(f"  Odds API: fetched {sport_key}/{market_key} "
          f"(credits used={used}, remaining={remaining})")

    events: list[dict] = []
    for g in resp.json():
        home, away = g.get("home_team", "Home"), g.get("away_team", "Away")
        books = []
        for bk in g.get("bookmakers", []):
            mkt = next((m for m in bk.get("markets", []) if m.get("key") == market_key), None)
            if not mkt:
                continue
            prices = {o["name"]: int(o["price"]) for o in mkt.get("outcomes", [])
                      if "name" in o and "price" in o}
            if len(prices) == 2:
                books.append({"book": bk["key"], "prices": prices})
        if len(books) >= 2:
            events.append({
                "external_id": g["id"],
                "sport_id": sport,
                "name": f"{away} @ {home}",
                "start_time": g.get("commence_time"),
                "market": market_name,
                "books": books,
            })
    print(f"  Parsed {len(events)} events with >=2 books for {sport}.")
    return events
