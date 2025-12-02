from __future__ import annotations

import os
from dataclasses import dataclass


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class FeedConfig:
    name: str
    url: str


def _parse_feeds(raw: str) -> list[FeedConfig]:
    """
    Parse RSS_FEEDS format:
    - Comma- or newline-separated items.
    - Each item: name|url (name required to label the feed in emails).
    """
    feeds: list[FeedConfig] = []
    # Support newline-separated (easier in .env) and comma-separated (single-line).
    parts = []
    for line in raw.replace(",", "\n").splitlines():
        item = line.strip()
        if item:
            parts.append(item)

    for item in parts:
        if "|" not in item:
            raise ValueError(f"Invalid RSS_FEEDS entry (expect name|url): {item}")
        name, url = item.split("|", 1)
        name = name.strip()
        url = url.strip()
        if not name or not url:
            raise ValueError(f"Invalid RSS_FEEDS entry (empty name or url): {item}")
        feeds.append(FeedConfig(name=name, url=url))
    if not feeds:
        raise ValueError("RSS_FEEDS is set but parsed as empty")
    return feeds


@dataclass
class Settings:
    feeds: list[FeedConfig]
    rss_verify_ssl: bool
    smtp_host: str
    smtp_port: int
    email_from: str
    email_to: list[str]
    smtp_username: str | None
    smtp_password: str | None
    smtp_ssl: bool
    email_subject: str
    entry_limit: int
    starttls: bool

    @classmethod
    def from_env(cls) -> "Settings":
        rss_feeds_raw = os.getenv("RSS_FEEDS")
        if rss_feeds_raw:
            feeds = _parse_feeds(rss_feeds_raw)
        else:
            rss_url = _require_env("RSS_FEED_URL")
            default_name = os.getenv("RSS_FEED_NAME", "RSS")
            feeds = [FeedConfig(name=default_name, url=rss_url)]

        rss_verify_ssl = _get_bool("RSS_VERIFY_SSL", True)
        smtp_host = _require_env("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        email_from = _require_env("EMAIL_FROM")
        to_raw = _require_env("EMAIL_TO")
        email_to = [addr.strip() for addr in to_raw.split(",") if addr.strip()]
        if not email_to:
            raise ValueError("EMAIL_TO must contain at least one email address")

        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")

        email_subject = os.getenv("EMAIL_SUBJECT", "Daily RSS Digest")
        entry_limit = int(os.getenv("ENTRY_LIMIT", "20"))
        starttls = _get_bool("SMTP_STARTTLS", True)
        smtp_ssl = _get_bool("SMTP_SSL", False)

        return cls(
            feeds=feeds,
            rss_verify_ssl=rss_verify_ssl,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            email_from=email_from,
            email_to=email_to,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            smtp_ssl=smtp_ssl,
            email_subject=email_subject,
            entry_limit=entry_limit,
            starttls=starttls,
        )
