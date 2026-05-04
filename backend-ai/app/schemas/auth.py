from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class UserPublic(BaseModel):
    id: int
    email: EmailStr
    name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class ChangePasswordBody(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self) -> "ChangePasswordBody":
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordApiV1(BaseModel):
    version: Literal["v1"] = "v1"
    message: str


class ResetPasswordBody(BaseModel):
    token: str = Field(..., min_length=8, max_length=512)
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("token", mode="before")
    @classmethod
    def strip_token(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "ResetPasswordBody":
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class ResetPasswordApiV1(BaseModel):
    version: Literal["v1"] = "v1"
    message: str


class ChangePasswordApiV1(BaseModel):
    version: Literal["v1"] = "v1"
    message: str


