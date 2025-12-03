from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import List, TypedDict

import feedparser
import requests


class RssItem(TypedDict):
    title: str
    link: str
    published: str | None
    published_dt: datetime | None
    summary: str | None


DISPLAY_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
BEIJING_TZ = timezone(timedelta(hours=8))


def _to_datetime(struct_time: time.struct_time | None) -> datetime | None:
    if not struct_time:
        return None
    return datetime.fromtimestamp(time.mktime(struct_time), tz=timezone.utc)


def fetch_entries(url: str, limit: int, verify_ssl: bool = True) -> List[RssItem]:
    headers = {"User-Agent": "MyRSS/1.0 (+https://example.com)"}
    resp = requests.get(url, timeout=20, verify=verify_ssl, headers=headers)
    resp.raise_for_status()

    feed = feedparser.parse(resp.content)
    if getattr(feed, "bozo", False):
        raise RuntimeError(f"Failed to parse RSS feed: {getattr(feed, 'bozo_exception', 'unknown error')}")

    items: List[RssItem] = []
    for entry in feed.entries[:limit]:
        published_dt = _to_datetime(
            entry.get("published_parsed") or entry.get("updated_parsed")
        )
        if published_dt:
            local_dt = published_dt.astimezone(BEIJING_TZ)
            published_str = local_dt.strftime(DISPLAY_TIME_FORMAT)
        else:
            published_str = None
        items.append(
            RssItem(
                title=entry.get("title", "(no title)"),
                link=entry.get("link", ""),
                published=published_str,
                published_dt=published_dt,
                summary=entry.get("summary"),
            )
        )
    return items


def filter_previous_day(entries: List[RssItem], now: datetime | None = None) -> List[RssItem]:
    """
    Keep only entries whose published date matches the previous UTC day.
    """
    current = now or datetime.now(timezone.utc)
    target_date = (current - timedelta(days=1)).date()
    filtered: List[RssItem] = []
    for item in entries:
        published_dt = item.get("published_dt")
        if published_dt and published_dt.date() == target_date:
            filtered.append(item)
    return filtered
