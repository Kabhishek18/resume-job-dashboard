from typing import Optional

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError("UNAUTHORIZED", "Missing or invalid Authorization header", status_code=401)
    token = authorization.split(" ", 1)[1].strip()
    user_id = decode_token(token)
    if user_id is None:
        raise AppError("UNAUTHORIZED", "Invalid or expired token", status_code=401)
    user = db.get(User, user_id)
    if user is None:
        raise AppError("UNAUTHORIZED", "User not found", status_code=401)
    return user
