from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

from .browser import browser_session
from .config import Settings
from .filters import today_in_israel
from .notifier import NtfyNotifier
from .search import dump_results, save_debug_screenshot, search_all_queries
from .state import NotificationState


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor tazkirim.gov.il and notify via ntfy")
    parser.add_argument("--env-file", help="Path to .env file")
    parser.add_argument("--dry-run", action="store_true", help="Print matches without sending notifications")
    parser.add_argument("--all-dates", action="store_true", help="Include all dates, not only today")
    parser.add_argument("--date", help="Override reference date (YYYY-MM-DD) for filtering")
    parser.add_argument("--debug-screenshot", help="Save a screenshot after the last search query")
    parser.add_argument("--headed", action="store_true", help="Run browser in headed mode")
    return parser.parse_args()


def run(settings: Settings, args: argparse.Namespace) -> int:
    reference_date = date.fromisoformat(args.date) if args.date else today_in_israel()
    only_today = not args.all_dates

    logger = logging.getLogger(__name__)
    logger.info(
        "Starting tazkirim monitor (only_today=%s, reference_date=%s, queries=%s)",
        only_today,
        reference_date,
        len(settings.search_queries),
    )

    with browser_session(settings, headless=not args.headed) as (_, _, page):
        results = search_all_queries(
            page,
            settings,
            only_today=only_today,
            reference_date=reference_date,
        )

        if args.debug_screenshot:
            save_debug_screenshot(page, args.debug_screenshot)

    logger.info("Matched %s result(s)", len(results))
    print(dump_results(results))

    if args.dry_run:
        logger.info("Dry run - skipping notifications")
        return 0

    if not settings.ntfy_topic:
        logger.error("NTFY_TOPIC is required unless --dry-run is used")
        return 2

    with NotificationState(settings.state_db_path) as state, NtfyNotifier(settings) as notifier:
        new_results = state.filter_new(results)
        logger.info("%s new result(s) to notify", len(new_results))

        for result in new_results:
            notifier.notify_item(result)
            state.mark_notified(result)

        if settings.send_heartbeat and not new_results:
            notifier.notify_heartbeat(len(results), 0)

    return 0


def main() -> None:
    args = parse_args()
    settings = Settings.from_env(args.env_file)
    configure_logging(settings.log_level)
    try:
        raise SystemExit(run(settings, args))
    except Exception:
        logging.exception("tazkirim monitor failed")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
