from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordApiV1,
    ChangePasswordBody,
    ForgotPasswordApiV1,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordApiV1,
    ResetPasswordBody,
    TokenResponse,
    UserPublic,
)
from app.services.password_reset import (
    FORGOT_PASSWORD_PUBLIC_MESSAGE_V1,
    complete_password_reset,
    change_password_logged_in,
    issue_password_reset_email,
)

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


@router.post("/change-password", response_model=ChangePasswordApiV1)
def change_password_route(
    body: ChangePasswordBody,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> ChangePasswordApiV1:
    change_password_logged_in(
        db=db,
        user=current,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    return ChangePasswordApiV1(
        version="v1",
        message="Your password has been updated. Sign in again on other devices if needed.",
    )


@router.post("/forgot-password", response_model=ForgotPasswordApiV1)
def forgot_password_route(body: ForgotPasswordRequest, db: Session = Depends(get_db)) -> ForgotPasswordApiV1:
    norm = body.email.strip().lower()
    user = db.scalar(select(User).where(User.email == norm))
    if user is not None:
        issue_password_reset_email(db=db, user=user, settings=settings)
    return ForgotPasswordApiV1(version="v1", message=FORGOT_PASSWORD_PUBLIC_MESSAGE_V1)


@router.post("/reset-password", response_model=ResetPasswordApiV1)
def reset_password_route(body: ResetPasswordBody, db: Session = Depends(get_db)) -> ResetPasswordApiV1:
    complete_password_reset(
        db=db,
        raw_token=body.token,
        new_password=body.new_password,
        settings=settings,
    )
    return ResetPasswordApiV1(
        version="v1",
        message="Your password has been updated. Sign in with your new password.",
    )
