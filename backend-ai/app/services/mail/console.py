import logging

from typing import Optional

from app.services.mail.base import MailSender


class ConsoleMailSender:
    """Logs email content — development / CI friendly."""

    def __init__(self, logger_name: str = "mail.console") -> None:
        self._log = logging.getLogger(logger_name)

    def send(self, to: str, subject: str, text_body: str, html_body: Optional[str] = None) -> None:
        self._log.info(
            "MAIL (console) to=%s subject=%s\n---\n%s\n--- html=%s",
            to,
            subject,
            text_body,
            "yes" if html_body else "no",
        )
