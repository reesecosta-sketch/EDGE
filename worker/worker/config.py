"""Environment-driven config. Secrets come from .env (git-ignored) — never hardcode."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:  # optional; the worker still runs if python-dotenv isn't installed
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except Exception:
    pass


@dataclass(frozen=True)
class Config:
    database_url: str | None = os.getenv("DATABASE_URL")
    supabase_url: str | None = os.getenv("SUPABASE_URL")
    service_role_key: str | None = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    odds_api_key: str | None = os.getenv("ODDS_API_KEY")
    odds_api_base: str = os.getenv("ODDS_API_BASE", "https://api.the-odds-api.com/v4")

    # Only surface bets above this EV (fraction, e.g. 0.02 = +2%).
    min_ev: float = float(os.getenv("MIN_EV", "0.02"))
    # Devig method used to compute the fair line: multiplicative | power | shin
    devig_method: str = os.getenv("DEVIG_METHOD", "multiplicative")
    # Fractional-Kelly scaler.
    kelly_fraction: float = float(os.getenv("KELLY_FRACTION", "0.25"))


CONFIG = Config()
