"""
Postgres writer (Supabase). Uses DATABASE_URL (service-role connection, bypasses
RLS) — the ONLY writer of the public model tables. Never ship these credentials
to the client. Guarded: if psycopg or DATABASE_URL is missing, --dry-run still runs.
"""
from __future__ import annotations

import json
import re
from typing import Any, Iterable
from urllib.parse import quote

from .config import CONFIG


def _normalize_dsn(dsn: str) -> str:
    """Percent-encode the password in a postgres URL so special characters (@, /,
    #, etc.) don't break libpq's URL parsing. Greedy match takes the LAST '@' as
    the host separator, so an '@' inside the password is handled correctly."""
    m = re.match(r"^(postgres(?:ql)?://[^:/@]+:)(.*)@([^@/]+.*)$", dsn)
    if not m:
        return dsn
    user_part, password, host_part = m.groups()
    if "%" in password:  # assume already-encoded; leave it alone
        return dsn
    return f"{user_part}{quote(password, safe='')}@{host_part}"


class Db:
    def __init__(self, dsn: str | None = None) -> None:
        raw = dsn or CONFIG.database_url
        self.dsn = _normalize_dsn(raw) if raw else raw
        if not self.dsn:
            raise RuntimeError(
                "DATABASE_URL not set. Fill .env (Supabase → Settings → Database → "
                "Connection string), or use --dry-run to skip the DB."
            )
        import psycopg  # imported lazily so --dry-run needs no driver
        self._psycopg = psycopg

    def _conn(self):
        return self._psycopg.connect(self.dsn, autocommit=True)

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
