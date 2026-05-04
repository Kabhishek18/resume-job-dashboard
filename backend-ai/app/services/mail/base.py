from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class MailSender(Protocol):
    def send(self, to: str, subject: str, text_body: str, html_body: Optional[str] = None) -> None:
        """Deliver mail. Raises on definitive failure."""
