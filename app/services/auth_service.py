from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from jose import JWTError, jwt
import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse, UserUpdateRequest


def _hash(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")


def _verify(plain: str, hashed: str) -> bool:
    pwd_bytes = plain.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hashed.encode("utf-8"))


def _make_tokens(user_id: UUID) -> TokenResponse:
    now = datetime.now(timezone.utc)
    access_payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    refresh_payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return TokenResponse(
        access_token=jwt.encode(access_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM),
        refresh_token=jwt.encode(refresh_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def _slug_from(text: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def register(self, payload: RegisterRequest) -> TokenResponse:
        existing = await self._get_user_by_email(payload.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "EMAIL_ALREADY_EXISTS", "message": "An account with this email already exists."},
            )
        user = User(
            email=payload.email,
            hashed_password=_hash(payload.password),
            full_name=payload.full_name,
            phone=payload.phone,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return _make_tokens(user.id)

    async def login(self, payload: LoginRequest) -> TokenResponse:
        user = await self._get_user_by_email(payload.email)
        if not user or not _verify(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_CREDENTIALS", "message": "Incorrect email or password."},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "ACCOUNT_DEACTIVATED", "message": "Your account has been deactivated."},
            )
        return _make_tokens(user.id)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": "Invalid or expired refresh token."},
            )
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN_TYPE", "message": "Expected a refresh token."},
            )
        user_id = payload.get("sub")
        result = await self.db.execute(select(User).where(User.id == UUID(user_id)))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "USER_NOT_FOUND", "message": "User no longer exists."},
            )
        return _make_tokens(user.id)

    async def logout(self, refresh_token: str) -> None:
        # Stateless JWT — token blacklisting can be added via Redis in v2
        pass

    async def update_profile(self, user: User, payload: UserUpdateRequest) -> User:
        if payload.full_name is not None:
            user.full_name = payload.full_name
        if payload.phone is not None:
            user.phone = payload.phone
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def change_password(self, user: User, payload: ChangePasswordRequest) -> None:
        if not _verify(payload.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "WRONG_PASSWORD", "message": "Current password is incorrect."},
            )
        user.hashed_password = _hash(payload.new_password)
        self.db.add(user)
        await self.db.flush()