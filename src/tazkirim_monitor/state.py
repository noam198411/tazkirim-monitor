from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

from .filters import SearchResult


class NotificationState:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notified_items (
                record_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                published_on TEXT NOT NULL,
                notified_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS empty_notifications (
                reference_date TEXT PRIMARY KEY,
                notified_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def was_notified(self, record_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM notified_items WHERE record_id = ?",
            (record_id,),
        ).fetchone()
        return row is not None

    def mark_notified(self, result: SearchResult) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO notified_items
            (record_id, title, url, published_on, notified_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                result.record_id,
                result.title,
                result.url,
                result.published_on.isoformat(),
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
        self._conn.commit()

    def filter_new(self, results: list[SearchResult]) -> list[SearchResult]:
        return [result for result in results if not self.was_notified(result.record_id)]

    def was_empty_notified(self, reference_date: date) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM empty_notifications WHERE reference_date = ?",
            (reference_date.isoformat(),),
        ).fetchone()
        return row is not None

    def mark_empty_notified(self, reference_date: date) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO empty_notifications
            (reference_date, notified_at)
            VALUES (?, ?)
            """,
            (reference_date.isoformat(), datetime.utcnow().isoformat(timespec="seconds")),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> NotificationState:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
