from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

try:
    # When executed as package module: python -m rss_mailer.runner
    from .config import Settings
    from .email_sender import (
        build_email,
        format_email_body,
        render_html_body,
        send_email,
    )
    from .rss_fetcher import fetch_entries
except ImportError:
    # Allow running via `python rss_mailer/runner.py`
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from rss_mailer.config import Settings  # type: ignore
    from rss_mailer.email_sender import (  # type: ignore
        build_email,
        format_email_body,
        render_html_body,
        send_email,
    )
    from rss_mailer.rss_fetcher import fetch_entries  # type: ignore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    load_dotenv()  # load .env if present
    try:
        settings = Settings.from_env()
    except Exception as exc:  # broad to show config errors immediately
        logger.error("Configuration error: %s", exc)
        return 1

    now_utc = datetime.now(timezone.utc)
    window_start = now_utc - timedelta(days=1)
    feed_entries = []

    for feed in settings.feeds:
        try:
            entries = fetch_entries(feed.url, settings.entry_limit, verify_ssl=settings.rss_verify_ssl)
        except Exception as exc:
            logger.error("Failed to fetch RSS feed '%s' (%s): %s", feed.name, feed.url, exc)
            continue

        filtered = [
            item
            for item in entries
            if (published_dt := item.get("published_dt")) and window_start <= published_dt <= now_utc
        ]
        feed_entries.append((feed.name, filtered))

    if not feed_entries:
        logger.error("No RSS feeds were fetched successfully.")
        return 1

    target_date_str = f"{window_start.isoformat()} to {now_utc.isoformat()}"

    body = format_email_body(feed_entries, target_date=target_date_str)
    html_body = render_html_body(feed_entries, target_date=target_date_str)
    message = build_email(
        subject=settings.email_subject,
        sender=settings.email_from,
        sender_name=settings.email_from_name,
        recipients=settings.email_to,
        text_body=body,
        html_body=html_body,
    )

    try:
        send_email(
            host=settings.smtp_host,
            port=settings.smtp_port,
            sender=settings.email_from,
            recipients=settings.email_to,
            message=message,
            username=settings.smtp_username,
            password=settings.smtp_password,
            starttls=settings.starttls,
            use_ssl=settings.smtp_ssl,
        )
        logger.info("Email sent to %s", ", ".join(settings.email_to))
        return 0
    except Exception as exc:
        logger.error(
            "Failed to send email (host=%s port=%s starttls=%s ssl=%s): %s",
            settings.smtp_host,
            settings.smtp_port,
            settings.starttls,
            settings.smtp_ssl,
            exc,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
