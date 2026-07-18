"""
Postgres writer (Supabase). Uses DATABASE_URL + the service role connection, which
bypasses RLS — this code is the ONLY writer of the public model tables. Never ship
these credentials to the client.

Guarded: if psycopg or DATABASE_URL is missing, callers can still run --dry-run,
which never touches the DB.
"""
from __future__ import annotations

from typing import Any, Iterable

from .config import CONFIG


class Db:
    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or CONFIG.database_url
        if not self.dsn:
            raise RuntimeError(
                "DATABASE_URL not set. Fill .env, or use --dry-run to skip the DB."
            )
        import psycopg  # imported lazily so --dry-run needs no driver
        self._psycopg = psycopg

    def _conn(self):
        return self._psycopg.connect(self.dsn, autocommit=True)

    def upsert_model_run(self, sport_id: str, version: str, metrics: dict) -> str:
        import json
        with self._conn() as c, c.cursor() as cur:
            cur.execute(
                "insert into model_runs (sport_id, model_version, metrics) "
                "values (%s, %s, %s) returning id",
                (sport_id, version, json.dumps(metrics)),
            )
            return str(cur.fetchone()[0])

    def insert_ev_bets(self, rows: Iterable[dict[str, Any]]) -> int:
        """rows: dicts matching ev_bets columns (see supabase/migrations)."""
        rows = list(rows)
        if not rows:
            return 0
        cols = ["sport_id", "event_id", "market", "selection", "book", "price",
                "model_prob", "novig_prob", "ev", "kelly_frac", "rationale",
                "prediction_id"]
        placeholders = ", ".join(["%s"] * len(cols))
        with self._conn() as c, c.cursor() as cur:
            cur.executemany(
                f"insert into ev_bets ({', '.join(cols)}) values ({placeholders})",
                [tuple(r.get(k) for k in cols) for r in rows],
            )
        return len(rows)
