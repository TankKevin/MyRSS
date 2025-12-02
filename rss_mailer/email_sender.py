from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Iterable

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

from .rss_fetcher import RssItem


def format_email_body(entries: Iterable[RssItem], target_date: str | None = None) -> str:
    """Plain-text fallback body."""
    lines: list[str] = []
    if target_date:
        lines.append(f"Entries for {target_date} (UTC)")
        lines.append("")
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
        lines.append("")  # blank line between entries

    if not lines or lines == ["", ""]:
        lines = []
    if not lines:
        lines.append("No new entries found.")
    return "\n".join(lines)


def render_html_body(entries: Iterable[RssItem], target_date: str | None = None) -> str | None:
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

    entries_list = list(entries)
    return template.render(entries=entries_list, target_date=target_date)


def build_email(
    subject: str,
    sender: str,
    recipients: list[str],
    text_body: str,
    html_body: str | None = None,
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
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
    with smtp_cls(host, port, timeout=30) as client:
        client.ehlo()
        if (not use_ssl) and starttls:
            client.starttls()
            client.ehlo()
        if username:
            client.login(username, password or "")
        client.sendmail(sender, recipients, message.as_string())
