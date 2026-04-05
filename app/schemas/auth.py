import re
from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)
    full_name: str = Field(min_length=2, max_length=150, strip_whitespace=True)
    phone: str | None = Field(default=None, pattern=r"^\+?[1-9]\d{9,14}$")

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Must contain at least one digit")
        if not re.search(r"[!@#$%^&*]", v):
            raise ValueError("Must contain at least one special character (!@#$%^&*)")
        return v

    @field_validator("full_name")
    @classmethod
    def no_digits_in_name(cls, v: str) -> str:
        if any(c.isdigit() for c in v):
            raise ValueError("Full name must not contain numbers")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=64)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Must contain at least one digit")
        if not re.search(r"[!@#$%^&*]", v):
            raise ValueError("Must contain at least one special character")
        return v