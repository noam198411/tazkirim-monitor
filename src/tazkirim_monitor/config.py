from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_SEARCH_QUERIES = [
    "עמדת טעינה",
    "תקנות החשמל",
    "תקנות משק החשמל",
    "תקנות מקורות האנרגיה",
    "טעינת רכב חשמלי",
    "לרכב חשמלי",
    "טעינת רכבים חשמיללים",
    "רכב חשמלי",
]

BASE_URL = "https://www.tazkirim.gov.il/s/?language=iw"
RESULT_LINK_SELECTOR = 'a[href*="legislativeworkactivity"], a[href*="law-item"]'
SEARCH_INPUT_SELECTOR = "input[aria-label*='חיפוש חופשי']"


@dataclass(frozen=True)
class Settings:
    ntfy_server: str
    ntfy_topic: str
    ntfy_priority: int
    log_level: str
    state_db_path: Path
    search_queries: list[str]
    send_heartbeat: bool
    page_load_timeout_ms: int
    search_wait_ms: int
    max_load_more_clicks: int

    @classmethod
    def from_env(cls, env_file: str | None = None) -> Settings:
        if env_file:
            load_dotenv(env_file, override=True)
        else:
            load_dotenv()

        queries_raw = os.getenv("SEARCH_QUERIES", "").strip()
        if queries_raw:
            search_queries = [q.strip() for q in queries_raw.split(",") if q.strip()]
        else:
            search_queries = list(DEFAULT_SEARCH_QUERIES)

        return cls(
            ntfy_server=os.getenv("NTFY_SERVER", "https://ntfy.sh").rstrip("/"),
            ntfy_topic=os.getenv("NTFY_TOPIC", "").strip(),
            ntfy_priority=int(os.getenv("NTFY_PRIORITY", "4")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            state_db_path=Path(os.getenv("STATE_DB_PATH", "./data/state.db")),
            search_queries=search_queries,
            send_heartbeat=os.getenv("SEND_HEARTBEAT", "false").lower() in {"1", "true", "yes"},
            page_load_timeout_ms=int(os.getenv("PAGE_LOAD_TIMEOUT_MS", "60000")),
            search_wait_ms=int(os.getenv("SEARCH_WAIT_MS", "12000")),
            max_load_more_clicks=int(os.getenv("MAX_LOAD_MORE_CLICKS", "20")),
        )
