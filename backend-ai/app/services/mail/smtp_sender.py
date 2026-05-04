from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional


class SmtpMailSender:
    """Synchronous SMTP; keep calls from sync FastAPI route handlers."""

    def __init__(
        self,
        host: str,
        port: int,
        *,
        use_tls: bool,
        username: str,
        password: str,
        mail_from: str,
    ) -> None:
        self._host = host
        self._port = port
        self._use_tls = use_tls
        self._username = username
        self._password = password
        self._mail_from = mail_from

    def send(self, to: str, subject: str, text_body: str, html_body: Optional[str] = None) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._mail_from
        msg["To"] = to
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        if html_body:
            msg.attach(MIMEText(html_body, "html", "utf-8"))

        if self._use_tls:
            with smtplib.SMTP(self._host, self._port) as smtp:
                smtp.starttls()
                if self._username:
                    smtp.login(self._username, self._password)
                smtp.sendmail(self._mail_from, [to], msg.as_string())
        else:
            with smtplib.SMTP(self._host, self._port) as smtp:
                if self._username:
                    smtp.login(self._username, self._password)
                smtp.sendmail(self._mail_from, [to], msg.as_string())
