from pydantic import BaseModel, EmailStr, Field, model_validator


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
