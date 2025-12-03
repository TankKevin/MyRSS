from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from typing import Iterable, List, Tuple

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

from .rss_fetcher import RssItem


def format_email_body(
    feed_entries: Iterable[Tuple[str, Iterable[RssItem]]],
    target_date: str | None = None,
) -> str:
    """Plain-text fallback body."""
    feeds: List[Tuple[str, List[RssItem]]] = [
        (name, list(entries)) for name, entries in feed_entries
    ]
    lines: list[str] = []
    if target_date:
        lines.append(f"Entries for {target_date} (UTC)")
        lines.append("")
    has_items = False
    for feed_name, entries in feeds:
        lines.append(f"[{feed_name}]")
        if entries:
            has_items = True
            for index, item in enumerate(entries, start=1):
                title = item.get("title") or "(no title)"
                link = item.get("link") or ""
                published = item.get("published")
                summary = item.get("summary")

                lines.append(f"{index}. {title}")
                if published:
                    lines.append(f"   Published (Beijing): {published}")
                if summary:
                    lines.append(f"   Summary: {summary}")
                if link:
                    lines.append(f"   Link: {link}")
                lines.append("")
        else:
            lines.append("   No entries in this window.")
            lines.append("")

    if not has_items and not feeds:
        lines.append("No new entries found.")
    elif not has_items:
        lines.append("No new entries found.")
    return "\n".join(lines)


def render_html_body(
    feed_entries: Iterable[Tuple[str, Iterable[RssItem]]],
    target_date: str | None = None,
) -> str | None:
    """Render HTML body with Jinja2 template (rss_mailer/templates/email.html)."""
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )
    try:
        template = env.get_template("email.html")
    except TemplateNotFound:
        return None

    feeds_list: List[Tuple[str, List[RssItem]]] = [
        (name, list(entries)) for name, entries in feed_entries
    ]
    return template.render(feeds=feeds_list, target_date=target_date)


def build_email(
    subject: str,
    sender: str,
    sender_name: str | None,
    recipients: list[str],
    text_body: str,
    html_body: str | None = None,
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((sender_name or "", sender))
    message["To"] = ", ".join(recipients)
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")
    return message


def send_email(
    host: str,
    port: int,
    sender: str,
    recipients: list[str],
    message: EmailMessage,
    username: str | None = None,
    password: str | None = None,
    starttls: bool = True,
    use_ssl: bool = False,
) -> None:
    smtp_cls = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
    try:
        with smtp_cls(host, port, timeout=30) as client:
            client.ehlo()
            if (not use_ssl) and starttls:
                client.starttls()
                client.ehlo()
            if username:
                client.login(username, password or "")
            client.sendmail(sender, recipients, message.as_string())
    except smtplib.SMTPResponseException as exc:
        # Some servers (e.g., smtp.qq.com) may emit (-1, b"\x00\x00\x00") even after
        # accepting the message. Treat that specific combo as success.
        if exc.smtp_code == -1 and exc.smtp_error == b"\x00\x00\x00":
            return
        raise
