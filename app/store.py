"""SQLite persistence for FRED benchmark snapshots only (no chat or user data)."""

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class DailySnapshot:
    snapshot_date: date
    rate_30y: float
    rate_15y: float
    source_obs_date_30: date
    source_obs_date_15: date
    fetched_at: datetime


class RateStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_snapshots (
                    snapshot_date TEXT PRIMARY KEY,
                    rate_30y REAL NOT NULL,
                    rate_15y REAL NOT NULL,
                    source_obs_date_30 TEXT NOT NULL,
                    source_obs_date_15 TEXT NOT NULL,
                    fetched_at TEXT NOT NULL
                )
                """
            )

    def upsert_snapshot(self, row: DailySnapshot) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO daily_snapshots (
                    snapshot_date, rate_30y, rate_15y,
                    source_obs_date_30, source_obs_date_15, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(snapshot_date) DO UPDATE SET
                    rate_30y = excluded.rate_30y,
                    rate_15y = excluded.rate_15y,
                    source_obs_date_30 = excluded.source_obs_date_30,
                    source_obs_date_15 = excluded.source_obs_date_15,
                    fetched_at = excluded.fetched_at
                """,
                (
                    row.snapshot_date.isoformat(),
                    row.rate_30y,
                    row.rate_15y,
                    row.source_obs_date_30.isoformat(),
                    row.source_obs_date_15.isoformat(),
                    row.fetched_at.isoformat(timespec="seconds"),
                ),
            )

    def latest_snapshot(self) -> Optional[DailySnapshot]:
        with self._conn() as conn:
            cur = conn.execute(
                """
                SELECT snapshot_date, rate_30y, rate_15y,
                       source_obs_date_30, source_obs_date_15, fetched_at
                FROM daily_snapshots
                ORDER BY snapshot_date DESC
                LIMIT 1
                """
            )
            r = cur.fetchone()
        if not r:
            return None
        return DailySnapshot(
            snapshot_date=date.fromisoformat(r["snapshot_date"]),
            rate_30y=r["rate_30y"],
            rate_15y=r["rate_15y"],
            source_obs_date_30=date.fromisoformat(r["source_obs_date_30"]),
            source_obs_date_15=date.fromisoformat(r["source_obs_date_15"]),
            fetched_at=datetime.fromisoformat(r["fetched_at"]),
        )
