from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.services.mail.factory import get_mail_sender

RESET_TOKEN_INVALID = AppError(
    "RESET_TOKEN_INVALID",
    "This reset link is invalid or has expired. Please request a new one.",
    status_code=400,
)

FORGOT_PASSWORD_PUBLIC_MESSAGE_V1 = (
    "If an account exists for that email address, we've sent instructions to reset your password."
)


def _token_material_pepper(settings: Settings) -> str:
    p = (settings.password_reset_pepper or "").strip()
    return p if p else settings.jwt_secret


def hash_reset_token_material(raw: str, settings: Settings) -> str:
    pepper = _token_material_pepper(settings)
    return hashlib.sha256(f"{pepper}\0{raw}".encode("utf-8")).hexdigest()


def generate_password_reset_raw_token() -> str:
    return secrets.token_urlsafe(32)


def issue_password_reset_email(*, db: Session, user: User, settings: Settings) -> None:
    raw = generate_password_reset_raw_token()
    th = hash_reset_token_material(raw, settings)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.password_reset_token_ttl_minutes)
    row = PasswordResetToken(user_id=user.id, token_hash=th, expires_at=expires_at)
    db.add(row)
    db.commit()

    origin = settings.frontend_origin_normalized
    if not origin:
        logging.getLogger(__name__).warning("FRONTEND_BASE_URL empty; reset link may be incomplete")
    reset_path = "/reset-password"
    link = f"{origin}{reset_path}?token={raw}"

    sender = get_mail_sender(settings)
    subject = "Reset your Resume Job Dashboard password"
    text = (
        "We received a request to reset your password.\n\n"
        f"{link}\n\n"
        "This link can be used once and expires automatically.\n"
        "If you did not ask for this, you can safely ignore this email."
    )
    html = (
        '<p>We received a request to reset your password.</p>'
        f'<p><a href="{link}">Choose a new password</a></p>'
        '<p>This link works once and expires automatically.</p>'
        "<p>If you did not ask for this, you can ignore this email.</p>"
    )
    try:
        sender.send(user.email, subject, text, html)
    except Exception:
        logging.getLogger(__name__).exception(
            "Failed to deliver password-reset email transport=%s to=%s",
            settings.mail_transport,
            user.email,
        )


def complete_password_reset(*, db: Session, raw_token: str, new_password: str, settings: Settings) -> None:
    th = hash_reset_token_material(raw_token.strip(), settings)
    now = datetime.now(timezone.utc)
    row = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == th,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
    )
    if row is None:
        raise RESET_TOKEN_INVALID

    user = db.get(User, row.user_id)
    if user is None:
        raise RESET_TOKEN_INVALID

    user.hashed_password = hash_password(new_password)
    row.used_at = now
    db.add(user)
    db.add(row)
    db.commit()


def change_password_logged_in(*, db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.hashed_password):
        raise AppError(
            "WRONG_CURRENT_PASSWORD",
            "Current password is incorrect.",
            status_code=400,
        )
    user.hashed_password = hash_password(new_password)
    db.add(user)
    db.commit()
