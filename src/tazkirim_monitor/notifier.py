from __future__ import annotations

import logging
import time

import httpx

from .config import Settings
from .filters import SearchResult

logger = logging.getLogger(__name__)


class NtfyNotifier:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.Client(timeout=30.0)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> NtfyNotifier:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _post(self, payload: dict) -> None:
        url = f"{self._settings.ntfy_server}/"
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                response = self._client.post(url, json=payload)
                response.raise_for_status()
                return
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning("ntfy attempt %s failed: %s", attempt, exc)
                time.sleep(attempt)
        raise RuntimeError(f"Failed to send ntfy notification after 3 attempts: {last_error}")

    def notify_item(self, result: SearchResult) -> None:
        ministry_line = f"\nמשרד: {result.ministry}" if result.ministry else ""
        message = (
            f"{result.title}\n"
            f"הופץ: {result.published_on.strftime('%d/%m/%Y')}\n"
            f"חיפוש: {result.search_query}"
            f"{ministry_line}"
        )
        payload = {
            "topic": self._settings.ntfy_topic,
            "title": f"תזכיר חדש: {result.title[:80]}",
            "message": message,
            "tags": ["tazkirim", "ev"],
            "click": result.url,
            "priority": self._settings.ntfy_priority,
        }
        self._post(payload)
        logger.info("Sent ntfy notification for %s", result.record_id)

    def notify_heartbeat(self, matched_count: int, sent_count: int) -> None:
        payload = {
            "topic": self._settings.ntfy_topic,
            "title": "Tazkirim monitor - no new items",
            "message": (
                f"Run completed.\n"
                f"Matched today: {matched_count}\n"
                f"New notifications sent: {sent_count}"
            ),
            "tags": ["tazkirim", "heartbeat"],
            "priority": 2,
        }
        self._post(payload)
