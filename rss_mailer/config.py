from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal, cast


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
    category: str = "General"


def _parse_feeds(raw: str) -> list[FeedConfig]:
    """
    Parse RSS_FEEDS format:
    - Comma- or newline-separated items.
    - Each item: category|name|url.
    - Legacy name|url entries are accepted and placed under "General".
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
            raise ValueError(f"Invalid RSS_FEEDS entry (expect category|name|url): {item}")
        fields = [field.strip() for field in item.split("|", 2)]
        if len(fields) == 2:
            category = "General"
            name, url = fields
        else:
            category, name, url = fields
        name = name.strip()
        url = url.strip()
        category = category.strip() or "General"
        if not category or not name or not url:
            raise ValueError(f"Invalid RSS_FEEDS entry (empty category, name, or url): {item}")
        feeds.append(FeedConfig(name=name, url=url, category=category))
    if not feeds:
        raise ValueError("RSS_FEEDS is set but parsed as empty")
    return feeds


DigestFrequency = Literal["daily", "weekly"]


@dataclass
class Settings:
    feeds: list[FeedConfig]
    rss_verify_ssl: bool
    smtp_host: str
    smtp_port: int
    email_from: str
    email_from_name: str | None
    email_to: list[str]
    email_hide_recipients: bool
    smtp_username: str | None
    smtp_password: str | None
    smtp_ssl: bool
    email_subject: str
    entry_limit: int
    starttls: bool
    digest_frequency: DigestFrequency
    ai_summary_enabled: bool
    zhipu_api_key: str | None
    zhipu_api_host: str
    zhipu_model: str
    ai_summary_max_items: int
    ai_summary_description_chars: int

    @classmethod
    def from_env(cls) -> "Settings":
        rss_feeds_raw = os.getenv("RSS_FEEDS")
        if rss_feeds_raw:
            feeds = _parse_feeds(rss_feeds_raw)
        else:
            rss_url = _require_env("RSS_FEED_URL")
            default_name = os.getenv("RSS_FEED_NAME", "RSS")
            default_category = os.getenv("RSS_FEED_CATEGORY", "General")
            feeds = [FeedConfig(name=default_name, url=rss_url, category=default_category)]

        rss_verify_ssl = _get_bool("RSS_VERIFY_SSL", True)
        smtp_host = _require_env("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        email_from = _require_env("EMAIL_FROM")
        email_from_name = os.getenv("EMAIL_FROM_NAME", "Kevin Tan")
        to_raw = _require_env("EMAIL_TO")
        email_to = [addr.strip() for addr in to_raw.split(",") if addr.strip()]
        if not email_to:
            raise ValueError("EMAIL_TO must contain at least one email address")

        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")

        digest_frequency = os.getenv("DIGEST_FREQUENCY", "daily").strip().lower()
        if digest_frequency not in {"daily", "weekly"}:
            raise ValueError("DIGEST_FREQUENCY must be 'daily' or 'weekly'")

        email_subject = os.getenv("EMAIL_SUBJECT", "Weekly AI Digest")
        entry_limit = int(os.getenv("ENTRY_LIMIT", "20"))
        starttls = _get_bool("SMTP_STARTTLS", True)
        smtp_ssl = _get_bool("SMTP_SSL", False)
        email_hide_recipients = _get_bool("EMAIL_HIDE_RECIPIENTS", False)
        zhipu_api_key = os.getenv("ZHIPU_API_KEY")
        ai_summary_enabled = _get_bool("AI_SUMMARY_ENABLED", bool(zhipu_api_key))
        zhipu_api_host = os.getenv(
            "ZHIPU_API_HOST",
            "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        )
        zhipu_model = os.getenv("ZHIPU_MODEL", "glm-4.7-flash")
        ai_summary_max_items = int(os.getenv("AI_SUMMARY_MAX_ITEMS", "30"))
        ai_summary_description_chars = int(os.getenv("AI_SUMMARY_DESCRIPTION_CHARS", "300"))

        return cls(
            feeds=feeds,
            rss_verify_ssl=rss_verify_ssl,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            email_from=email_from,
            email_from_name=email_from_name,
            email_to=email_to,
            email_hide_recipients=email_hide_recipients,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            smtp_ssl=smtp_ssl,
            email_subject=email_subject,
            entry_limit=entry_limit,
            starttls=starttls,
            digest_frequency=cast(DigestFrequency, digest_frequency),
            ai_summary_enabled=ai_summary_enabled,
            zhipu_api_key=zhipu_api_key,
            zhipu_api_host=zhipu_api_host,
            zhipu_model=zhipu_model,
            ai_summary_max_items=ai_summary_max_items,
            ai_summary_description_chars=ai_summary_description_chars,
        )
