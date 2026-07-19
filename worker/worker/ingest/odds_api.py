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


# ---- multi-sport discovery (for the daily --all run) -------------------------

# EXACT keys for team sports (group-matching wrongly grabbed KBO as "MLB" and
# NCAAF as "NFL"). Golf/NASCAR use per-tournament outright keys that rotate, so
# those are discovered by group among currently-active events.
EXACT_KEYS = {"baseball_mlb": "mlb", "americanfootball_nfl": "nfl"}
SOCCER_PREF = ("soccer_usa_mls", "soccer_uefa_champs_league",
               "soccer_conmebol_copa_libertadores", "soccer_brazil_campeonato")
KEY_CAP = {"mlb": 1, "nfl": 1, "soccer": 2, "golf": 2, "nascar": 1}
_MARKET_NAME = {"h2h": "moneyline", "outrights": "outright"}


def _get(path: str, params: dict):
    import httpx
    if not CONFIG.odds_api_key:
        raise RuntimeError("ODDS_API_KEY is not set (get a free key at the-odds-api.com).")
    resp = httpx.get(f"{CONFIG.odds_api_base}{path}",
                     params={**params, "apiKey": CONFIG.odds_api_key}, timeout=30)
    resp.raise_for_status()
    return resp


def discover_active_keys() -> list[tuple[str, str, str]]:
    """Query /sports (free) and pick ACTIVE keys for exactly our target leagues.
    Returns [(odds_api_key, internal_sport_id, market), ...]."""
    active = [s for s in _get("/sports", {}).json() if s.get("active")]
    picked: list[tuple[str, str, str]] = []
    counts: dict[str, int] = {}

    def add(key: str, sport_id: str, market: str) -> None:
        if counts.get(sport_id, 0) >= KEY_CAP.get(sport_id, 2):
            return
        counts[sport_id] = counts.get(sport_id, 0) + 1
        picked.append((key, sport_id, market))

    for s in active:
        key, grp = s.get("key", ""), s.get("group")
        if key in EXACT_KEYS:                                   # MLB, NFL (exact)
            add(key, EXACT_KEYS[key], "h2h")
        elif grp == "Golf" and s.get("has_outrights"):          # active tournaments
            add(key, "golf", "outrights")
        elif grp == "Motorsport" and s.get("has_outrights") \
                and "nascar" in (key + s.get("title", "")).lower():
            add(key, "nascar", "outrights")

    # Soccer: prefer known active leagues (MLS etc.), else the first couple.
    soccer = [s["key"] for s in active
              if s.get("group") == "Soccer" and not s.get("has_outrights")]
    for k in ([k for k in SOCCER_PREF if k in soccer] or soccer)[:KEY_CAP["soccer"]]:
        add(k, "soccer", "h2h")

    return picked


def _parse_events(payload: list, sport_id: str, market: str) -> list[dict]:
    events = []
    for g in payload:
        if market == "outrights":
            name = g.get("sport_title") or sport_id.title()
        else:
            name = f"{g.get('away_team', 'Away')} @ {g.get('home_team', 'Home')}"
        books = []
        for bk in g.get("bookmakers", []):
            mkt = next((m for m in bk.get("markets", []) if m.get("key") == market), None)
            if not mkt:
                continue
            prices = {o["name"]: int(o["price"]) for o in mkt.get("outcomes", [])
                      if "name" in o and "price" in o}
            if len(prices) >= 2:
                books.append({"book": bk["key"], "prices": prices})
        if len(books) >= 2:
            events.append({
                "external_id": g["id"], "sport_id": sport_id, "name": name,
                "start_time": g.get("commence_time"),
                "market": _MARKET_NAME.get(market, market), "books": books,
            })
    return events


def fetch_all(regions: str = "us") -> list[dict]:
    """Discover active target sports and fetch odds for each. Skips sports that
    error or are out of season. Returns normalized events across all sports."""
    keys = discover_active_keys()
    if not keys:
        print("  No active target sports found on the API right now.")
        return []
    all_events: list[dict] = []
    for key, sport_id, market in keys:
        try:
            resp = _get(f"/sports/{key}/odds",
                        {"regions": regions, "markets": market,
                         "oddsFormat": "american", "dateFormat": "iso"})
            evs = _parse_events(resp.json(), sport_id, market)
            rem = resp.headers.get("x-requests-remaining")
            print(f"  {sport_id:<7} {key:<44} {len(evs):>3} events (credits left={rem})")
            all_events.extend(evs)
        except Exception as e:  # noqa: BLE001 — one bad sport shouldn't kill the run
            print(f"  {sport_id:<7} {key:<44} skipped ({type(e).__name__})")
    return all_events
