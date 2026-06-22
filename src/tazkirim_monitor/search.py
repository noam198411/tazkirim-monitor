from __future__ import annotations

import json
import logging
import re
from datetime import date

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from .config import BASE_URL, RESULT_LINK_SELECTOR, SEARCH_INPUT_SELECTOR, Settings
from .filters import (
    SearchResult,
    extract_ministry_from_card,
    extract_record_id,
    is_published_today,
    parse_publish_date_from_card,
    today_in_israel,
)

logger = logging.getLogger(__name__)

EXTRACT_RESULTS_JS = """
(query) => {
    const anchors = Array.from(document.querySelectorAll(
        'a[href*="legislativeworkactivity"], a[href*="law-item"]'
    ));
    const seen = new Set();
    const results = [];
    for (const anchor of anchors) {
        const href = anchor.href.split('?')[0];
        const title = anchor.innerText.trim();
        if (!title || title.length < 10 || seen.has(href)) {
            continue;
        }
        let card = anchor.closest('article, li, div[class*="result"], .slds-card');
        if (!card) {
            let node = anchor.parentElement;
            for (let depth = 0; depth < 6 && node; depth++) {
                if (node.innerText && node.innerText.includes('|') && node.innerText.length < 2500) {
                    card = node;
                    break;
                }
                node = node.parentElement;
            }
        }
        const cardText = card ? card.innerText : '';
        seen.add(href);
        results.push({ href, title, cardText, searchQuery: query });
    }
    return results;
}
"""


def _parse_total_results(page: Page) -> int | None:
    match = re.search(r"\((\d+)\s+תוצאות חיפוש\)", page.inner_text("body"))
    if not match:
        return None
    return int(match.group(1))


def _click_load_more(page: Page) -> bool:
    candidates = [
        page.locator("button").filter(has_text=re.compile(r"^עוד$")),
        page.locator("a, button").filter(has_text=re.compile(r"טען עוד|הצג עוד|עוד תוצאות")),
    ]
    for locator in candidates:
        count = locator.count()
        for index in range(count):
            button = locator.nth(index)
            try:
                if not button.is_visible():
                    continue
                button.scroll_into_view_if_needed(timeout=3000)
                before = page.locator(RESULT_LINK_SELECTOR).count()
                button.click(timeout=5000)
                page.wait_for_timeout(2500)
                after = page.locator(RESULT_LINK_SELECTOR).count()
                if after > before:
                    logger.info("Loaded more results: %s -> %s", before, after)
                    return True
            except PlaywrightTimeoutError:
                continue
    return False


def _load_all_results(page: Page, settings: Settings) -> None:
    expected = _parse_total_results(page)
    for attempt in range(settings.max_load_more_clicks):
        current = page.locator(RESULT_LINK_SELECTOR).count()
        if expected is not None and current >= expected:
            break
        if not _click_load_more(page):
            break
        logger.debug("Load-more attempt %s", attempt + 1)


def _run_search(page: Page, settings: Settings, query: str) -> list[dict]:
    logger.info("Searching for: %s", query)
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=settings.page_load_timeout_ms)
    page.wait_for_timeout(3000)

    search_input = page.locator(SEARCH_INPUT_SELECTOR).first
    search_input.wait_for(state="visible", timeout=settings.page_load_timeout_ms)
    search_input.fill(query)
    page.keyboard.press("Enter")
    page.wait_for_timeout(settings.search_wait_ms)

    _load_all_results(page, settings)
    raw_items = page.evaluate(EXTRACT_RESULTS_JS, query)
    logger.info("Found %s raw results for query '%s'", len(raw_items), query)
    return raw_items


def _to_search_result(raw: dict, query: str) -> SearchResult | None:
    record_id = extract_record_id(raw["href"])
    if not record_id:
        logger.warning("Skipping result without record id: %s", raw["href"])
        return None

    published_on = parse_publish_date_from_card(raw.get("cardText", ""))
    if published_on is None:
        logger.warning("Could not parse publish date for %s", raw["title"])
        return None

    return SearchResult(
        record_id=record_id,
        title=raw["title"],
        url=raw["href"],
        published_on=published_on,
        search_query=query,
        ministry=extract_ministry_from_card(raw.get("cardText", "")),
    )


def search_query(page: Page, settings: Settings, query: str) -> list[SearchResult]:
    raw_items = _run_search(page, settings, query)
    results: list[SearchResult] = []
    for raw in raw_items:
        item = _to_search_result(raw, query)
        if item is not None:
            results.append(item)
    return results


def search_all_queries(
    page: Page,
    settings: Settings,
    *,
    only_today: bool = True,
    reference_date: date | None = None,
) -> list[SearchResult]:
    merged: dict[str, SearchResult] = {}
    reference = reference_date or today_in_israel()

    for query in settings.search_queries:
        for result in search_query(page, settings, query):
            if only_today and not is_published_today(result.published_on, reference):
                continue
            existing = merged.get(result.record_id)
            if existing is None:
                merged[result.record_id] = result
            elif query not in existing.search_query:
                merged[result.record_id] = SearchResult(
                    record_id=result.record_id,
                    title=result.title,
                    url=result.url,
                    published_on=result.published_on,
                    search_query=f"{existing.search_query}, {query}",
                    ministry=result.ministry or existing.ministry,
                )

    return list(merged.values())


def save_debug_screenshot(page: Page, path: str) -> None:
    page.screenshot(path=path, full_page=True)
    logger.info("Saved debug screenshot to %s", path)


def dump_results(results: list[SearchResult]) -> str:
    payload = [
        {
            "record_id": item.record_id,
            "title": item.title,
            "url": item.url,
            "published_on": item.published_on.isoformat(),
            "search_query": item.search_query,
            "ministry": item.ministry,
        }
        for item in results
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2)
