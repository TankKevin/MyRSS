from __future__ import annotations

import html
import logging
from typing import Iterable, Tuple

import requests

from .rss_fetcher import RssItem

logger = logging.getLogger(__name__)

FeedEntries = Iterable[Tuple[str, str, Iterable[RssItem]]]
SummaryEntry = Tuple[str, str, RssItem]
AI_SUMMARY_CATEGORY_LIMITS = {
    "Big Three": 10,
    "AI Business": 5,
    "AI Technology": 3,
}


def _strip_html(value: str | None) -> str:
    if not value:
        return ""
    text = html.unescape(value)
    in_tag = False
    chars: list[str] = []
    for char in text:
        if char == "<":
            in_tag = True
            chars.append(" ")
            continue
        if char == ">":
            in_tag = False
            continue
        if not in_tag:
            chars.append(char)
    return " ".join("".join(chars).split())


def _truncate_text(value: str, max_chars: int) -> str:
    if max_chars <= 0 or len(value) <= max_chars:
        return value
    return value[:max_chars].rstrip() + "..."


def _category_item_limit(category: str, max_items: int) -> int | None:
    if category in AI_SUMMARY_CATEGORY_LIMITS:
        return AI_SUMMARY_CATEGORY_LIMITS[category]
    return max_items


def _select_summary_entries(feed_entries: FeedEntries, max_items: int) -> list[SummaryEntry]:
    grouped_entries: dict[str, list[tuple[str, list[RssItem]]]] = {}
    for category, feed_name, entries in feed_entries:
        grouped_entries.setdefault(category, []).append((feed_name, list(entries)))

    selected: list[SummaryEntry] = []
    for category, feed_blocks in grouped_entries.items():
        category_limit = _category_item_limit(category, max_items)
        selected_count = 0
        cursors = [0 for _feed_name, _entries in feed_blocks]
        while category_limit is None or selected_count < category_limit:
            added_in_round = False
            for index, (feed_name, entries) in enumerate(feed_blocks):
                if category_limit is not None and selected_count >= category_limit:
                    break
                if cursors[index] >= len(entries):
                    continue
                selected.append((category, feed_name, entries[cursors[index]]))
                cursors[index] += 1
                selected_count += 1
                added_in_round = True
            if not added_in_round:
                break
    return selected


def _entry_lines(feed_entries: FeedEntries, max_items: int, description_chars: int) -> list[str]:
    lines: list[str] = []
    for category, feed_name, item in _select_summary_entries(feed_entries, max_items):
        title = item.get("title") or "(no title)"
        description = _truncate_text(_strip_html(item.get("summary")), description_chars)
        if description:
            lines.append(
                f"Area: {category}\nSource: {feed_name}\n"
                f"Title: {title}\nDescription excerpt: {description}"
            )
        else:
            lines.append(f"Area: {category}\nSource: {feed_name}\nTitle: {title}\nDescription excerpt: ")
    return lines


def build_summary_prompt(
    feed_entries: FeedEntries,
    target_date: str,
    max_items: int,
    description_chars: int,
) -> str:
    entry_lines = _entry_lines(
        feed_entries,
        max_items=max_items,
        description_chars=description_chars,
    )
    if not entry_lines:
        return ""

    entries_text = "\n\n".join(f"{index}. {line}" for index, line in enumerate(entry_lines, start=1))
    return (
        "You are writing the opening AI summary for an RSS email digest.\n"
        "Write in concise English.\n"
        "Return an HTML fragment only. Do not wrap it in html, body, or code fences.\n"
        "Use only these tags: <p>, <ul>, <li>, <strong>.\n"
        "Do not include attributes, links, scripts, styles, markdown, or tables.\n"
        "Use this structure:\n"
        "1. One <p> with one sentence overall trend across all areas.\n"
        "2. For each area with entries, add one <p><strong>{exact area name}:</strong> short area summary.</p>, "
        "then one <ul> with 1-3 <li> highlights for that area.\n"
        "3. Areas must stay separate and use these names when present: Big Three, AI Business, AI Technology.\n"
        "4. One final <p> with one short sentence on what to watch next.\n\n"
        f"Digest window: {target_date}\n"
        f"RSS entries:\n{entries_text}"
    )


def generate_ai_summary(
    feed_entries: FeedEntries,
    target_date: str,
    api_key: str,
    api_host: str,
    model: str,
    max_items: int,
    description_chars: int,
) -> str | None:
    prompt = build_summary_prompt(
        feed_entries,
        target_date=target_date,
        max_items=max_items,
        description_chars=description_chars,
    )
    if not prompt:
        return None

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You summarize RSS digests for a busy technology reader.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "stream": False,
        "temperature": 0.3,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(api_host, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.error("Failed to generate AI summary with Zhipu AI: %s", exc)
        return None

    summary = str(content).strip()
    return summary or None
