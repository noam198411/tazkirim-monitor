from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from dateutil import parser as date_parser

ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")
DATE_IN_CARD_RE = re.compile(r"\d{1,2}/\d{1,2}/\d{4}")
RECORD_ID_RE = re.compile(r"/(a[a-zA-Z0-9]{15,18})(?:/|$|\?)")


@dataclass(frozen=True)
class SearchResult:
    record_id: str
    title: str
    url: str
    published_on: date
    search_query: str
    ministry: str | None = None


def today_in_israel() -> date:
    return datetime.now(ISRAEL_TZ).date()


def extract_record_id(url: str) -> str | None:
    match = RECORD_ID_RE.search(url)
    return match.group(1) if match else None


def parse_publish_date_from_card(card_text: str) -> date | None:
    for line in card_text.splitlines():
        if "|" not in line:
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 2:
            continue
        candidate = parts[1]
        if not DATE_IN_CARD_RE.fullmatch(candidate):
            continue
        try:
            parsed = date_parser.parse(candidate, dayfirst=True).date()
        except (ValueError, OverflowError):
            continue
        return parsed

    match = DATE_IN_CARD_RE.search(card_text)
    if not match:
        return None
    try:
        return date_parser.parse(match.group(0), dayfirst=True).date()
    except (ValueError, OverflowError):
        return None


def extract_ministry_from_card(card_text: str) -> str | None:
    for line in card_text.splitlines():
        if "|" not in line:
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) >= 4 and parts[3]:
            return parts[3]
    return None


def is_published_today(published_on: date, reference: date | None = None) -> bool:
    reference_date = reference or today_in_israel()
    return published_on == reference_date
