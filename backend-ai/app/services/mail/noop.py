from typing import Optional

from app.services.mail.base import MailSender


class NoopMailSender:
    """Discards mail without sending."""

    def send(self, to: str, subject: str, text_body: str, html_body: Optional[str] = None) -> None:
        pass
