from __future__ import annotations

import os
import re
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from typing import Iterable, Tuple, TypedDict

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

from .rss_fetcher import RssItem


class FeedBlock(TypedDict):
    name: str
    anchor: str
    items: list[RssItem]


class CategorySection(TypedDict):
    title: str
    anchor: str
    feeds: list[FeedBlock]
    count: int


FeedEntries = Iterable[Tuple[str, str, Iterable[RssItem]]]


def _anchor_for_label(prefix: str, label: str, index: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return f"{prefix}-{slug or index}"


def _unique_anchor(base_anchor: str, used_anchors: set[str], index: int) -> str:
    anchor = base_anchor
    while anchor in used_anchors:
        anchor = f"{base_anchor}-{index}"
        index += 1
    used_anchors.add(anchor)
    return anchor


def _build_sections(feed_entries: FeedEntries) -> list[CategorySection]:
    sections: list[CategorySection] = []
    section_indexes: dict[str, int] = {}
    used_anchors: set[str] = set()

    for category, feed_name, entries in feed_entries:
        entries_list = list(entries)
        if category not in section_indexes:
            section_index = len(sections) + 1
            anchor = _unique_anchor(
                _anchor_for_label("section", category, section_index),
                used_anchors,
                section_index,
            )
            section_indexes[category] = len(sections)
            sections.append(
                CategorySection(
                    title=category,
                    anchor=anchor,
                    feeds=[],
                    count=0,
                )
            )

        section = sections[section_indexes[category]]
        feed_index = sum(len(item["feeds"]) for item in sections) + 1
        feed_anchor = _unique_anchor(
            _anchor_for_label("feed", feed_name, feed_index),
            used_anchors,
            feed_index,
        )
        section["feeds"].append(FeedBlock(name=feed_name, anchor=feed_anchor, items=entries_list))
        section["count"] += len(entries_list)

    return sections


def format_email_body(
    feed_entries: FeedEntries,
    target_date: str | None = None,
    ai_summary: str | None = None,
) -> str:
    """Plain-text fallback body."""
    sections = _build_sections(feed_entries)
    lines: list[str] = []
    if target_date:
        lines.append(f"Entries for {target_date} (UTC)")
        lines.append("")
    if ai_summary:
        lines.append("Highlights")
        lines.append(ai_summary.strip())
        lines.append("")
    has_items = False
    for section in sections:
        lines.append(f"## {section['title']}")
        lines.append("")
        for feed in section["feeds"]:
            feed_name = feed["name"]
            entries = feed["items"]
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
                        lines.append(f"   Published: {published}")
                    if summary:
                        lines.append(f"   Summary: {summary}")
                    if link:
                        lines.append(f"   Link: {link}")
                    lines.append("")
            else:
                lines.append("   No entries in this window.")
                lines.append("")

    if not has_items and not sections:
        lines.append("No new entries found.")
    elif not has_items:
        lines.append("No new entries found.")
    return "\n".join(lines)


def render_html_body(
    feed_entries: FeedEntries,
    target_date: str | None = None,
    ai_summary: str | None = None,
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

    sections = _build_sections(feed_entries)
    return template.render(
        sections=sections,
        target_date=target_date,
        ai_summary=ai_summary,
    )


def build_email(
    subject: str,
    sender: str,
    sender_name: str | None,
    recipients: list[str],
    text_body: str,
    html_body: str | None = None,
    hide_recipients: bool = False,
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((sender_name or "", sender))
    if hide_recipients:
        # Avoid listing all recipients in the headers; use sender as visible "To".
        message["To"] = sender
    else:
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
