from __future__ import annotations

import html
import logging
from typing import Iterable, Tuple

import requests

from .rss_fetcher import RssItem

logger = logging.getLogger(__name__)

FeedEntries = Iterable[Tuple[str, str, Iterable[RssItem]]]


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


def _entry_lines(feed_entries: FeedEntries, max_items: int, description_chars: int) -> list[str]:
    lines: list[str] = []
    for _category, _feed_name, entries in feed_entries:
        for item in entries:
            if len(lines) >= max_items:
                return lines
            title = item.get("title") or "(no title)"
            description = _truncate_text(_strip_html(item.get("summary")), description_chars)
            if description:
                lines.append(f"Title: {title}\nDescription excerpt: {description}")
            else:
                lines.append(f"Title: {title}\nDescription excerpt: ")
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
        "Return plain text only, no markdown table.\n"
        "Use this structure:\n"
        "1. One sentence overall trend.\n"
        "2. 3-5 bullet points with the most important updates.\n"
        "3. One short sentence on what to watch next.\n\n"
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
