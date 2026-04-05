import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    phone: str | None
    role: str
    is_active: bool
    created_at: datetime


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150, strip_whitespace=True)
    phone: str | None = Field(default=None, pattern=r"^\+?[1-9]\d{9,14}$")


class AdminUserUpdateRequest(BaseModel):
    is_active: bool | None = None
    role: Literal["customer", "admin"] | None = None