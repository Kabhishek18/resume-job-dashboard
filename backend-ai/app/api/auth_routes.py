from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserPublic

router = APIRouter(tags=["auth"])


def _user_public(user: User) -> UserPublic:
    return UserPublic(id=user.id, email=user.email, name=user.name)


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    existing = db.scalar(select(User).where(User.email == body.email.lower()))
    if existing is not None:
        raise AppError("EMAIL_TAKEN", "An account with this email already exists")

    user = User(
        email=body.email.lower(),
        name=body.name.strip(),
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=_user_public(user))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not verify_password(body.password, user.hashed_password):
        raise AppError(
            "INVALID_CREDENTIALS",
            "Invalid email or password",
            status_code=401,
        )

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=_user_public(user))


@router.get("/me", response_model=UserPublic)
def me(current: User = Depends(get_current_user)) -> UserPublic:
    return _user_public(current)
