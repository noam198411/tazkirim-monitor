from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from playwright.sync_api import Browser, Page, Playwright, sync_playwright

from .config import Settings


@contextmanager
def browser_session(settings: Settings, headless: bool = True) -> Iterator[tuple[Playwright, Browser, Page]]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page(
            locale="he-IL",
            viewport={"width": 1400, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page.set_default_timeout(settings.page_load_timeout_ms)
        try:
            yield playwright, browser, page
        finally:
            browser.close()
