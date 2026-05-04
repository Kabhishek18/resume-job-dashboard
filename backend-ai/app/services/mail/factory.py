from __future__ import annotations

import logging

from app.core.config import Settings
from app.services.mail.base import MailSender
from app.services.mail.console import ConsoleMailSender
from app.services.mail.noop import NoopMailSender
from app.services.mail.smtp_sender import SmtpMailSender


def mail_sender_from_settings(s: Settings) -> MailSender:
    t = (s.mail_transport or "noop").lower().strip()
    if t in ("noop", "none"):
        return NoopMailSender()
    if t == "console":
        return ConsoleMailSender()
    if t != "smtp":
        logging.getLogger(__name__).warning("Unknown MAIL_TRANSPORT=%r; using noop.", t)
        return NoopMailSender()

    missing = []
    if not (s.mail_smtp_host or "").strip():
        missing.append("MAIL_SMTP_HOST")
    port = getattr(s, "mail_smtp_port", 587)
    if not port or port <= 0:
        missing.append("MAIL_SMTP_PORT")
    if not (s.mail_from or "").strip():
        missing.append("MAIL_FROM")
    if missing:
        raise ValueError(f"MAIL_TRANSPORT=smtp requires: {', '.join(missing)}")

    user = (s.mail_smtp_username or "").strip()
    pwd = s.mail_smtp_password or ""

    return SmtpMailSender(
        host=s.mail_smtp_host.strip(),
        port=int(port),
        use_tls=s.mail_smtp_use_tls,
        username=user,
        password=pwd,
        mail_from=s.mail_from.strip(),
    )


def get_mail_sender(settings: Settings) -> MailSender:
    """Build a sender from resolved settings (new instance each call — test-friendly)."""
    return mail_sender_from_settings(settings)
