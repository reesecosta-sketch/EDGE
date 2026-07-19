"""
Postgres writer (Supabase). Uses DATABASE_URL (service-role connection, bypasses
RLS) — the ONLY writer of the public model tables. Never ship these credentials
to the client. Guarded: if psycopg or DATABASE_URL is missing, --dry-run still runs.
"""
from __future__ import annotations

import json
import re
from typing import Any, Iterable

from .config import CONFIG


def _pg_params(url: str) -> dict | None:
    """Parse a postgres URL into connection kwargs by string-splitting (robust to
    ANY special char in the password). Passing the password as a literal kwarg
    (not inside a URL) sidesteps all url-encoding issues.
      last '@'  -> splits userinfo from host   (host has no '@')
      first ':' -> splits user from password   (postgres user has no ':')"""
    if "://" not in url:
        return None
    scheme, rest = url.split("://", 1)
    if "postgres" not in scheme or "@" not in rest:
        return None
    userinfo, hostpart = rest.rsplit("@", 1)
    if ":" not in userinfo:
        return None
    user, password = userinfo.split(":", 1)
    hostport, _, dbname = hostpart.partition("/")
    host, _, port = hostport.partition(":")
    return {"user": user, "password": password, "host": host,
            "port": int(port or 5432), "dbname": dbname or "postgres"}


class Db:
    def __init__(self, dsn: str | None = None) -> None:
        raw = dsn or CONFIG.database_url
        if not raw:
            raise RuntimeError(
                "DATABASE_URL not set. Fill .env (Supabase → Settings → Database → "
                "Connection string), or use --dry-run to skip the DB."
            )
        self._params = _pg_params(raw)
        if self._params is None:
            raise RuntimeError(
                "DATABASE_URL is malformed. Expected "
                "postgresql://postgres:PASSWORD@db.<ref>.supabase.co:5432/postgres "
                "— check that the '@' before the host is present. Tip: copy the URI "
                "fresh from Supabase → Settings → Database → Connection string, and "
                "only replace the password."
            )
        import psycopg  # imported lazily so --dry-run needs no driver
        self._psycopg = psycopg

    def _conn(self):
        return self._psycopg.connect(autocommit=True, **self._params)

    def ensure_sport(self, sport_id: str, name: str) -> None:
        with self._conn() as c, c.cursor() as cur:
            cur.execute(
                "insert into sports (id, name) values (%s, %s) on conflict do nothing",
                (sport_id, name),
            )

    def upsert_event(self, sport_id: str, external_id: str, name: str,
                     start_time: str | None) -> str:
        with self._conn() as c, c.cursor() as cur:
            cur.execute(
                """insert into events (sport_id, external_id, name, start_time, status)
                   values (%s, %s, %s, coalesce(%s::timestamptz, now()), 'scheduled')
                   on conflict (sport_id, external_id)
                   do update set name = excluded.name, start_time = excluded.start_time
                   returning id""",
                (sport_id, external_id, name, start_time),
            )
            return str(cur.fetchone()[0])

    def clear_open(self, sport_id: str) -> int:
        """Remove the previous open board for a sport before writing a fresh one."""
        with self._conn() as c, c.cursor() as cur:
            cur.execute(
                "delete from ev_bets where sport_id = %s and status = 'open'",
                (sport_id,),
            )
            return cur.rowcount

    def upsert_model_run(self, sport_id: str, version: str, metrics: dict) -> str:
        with self._conn() as c, c.cursor() as cur:
            cur.execute(
                "insert into model_runs (sport_id, model_version, metrics) "
                "values (%s, %s, %s) returning id",
                (sport_id, version, json.dumps(metrics)),
            )
            return str(cur.fetchone()[0])

    def insert_ev_bets(self, rows: Iterable[dict[str, Any]]) -> int:
        """rows: dicts matching ev_bets columns. prediction_id may be None
        (line-shopping bets have no model prediction; 0003 makes it nullable)."""
        rows = list(rows)
        if not rows:
            return 0
        cols = ["sport_id", "event_id", "market", "selection", "book", "price",
                "model_prob", "novig_prob", "ev", "kelly_frac", "rationale",
                "prediction_id", "status"]
        placeholders = ", ".join(["%s"] * len(cols))
        with self._conn() as c, c.cursor() as cur:
            cur.executemany(
                f"insert into ev_bets ({', '.join(cols)}) values ({placeholders})",
                [tuple(r.get(k) for k in cols) for r in rows],
            )
        return len(rows)
