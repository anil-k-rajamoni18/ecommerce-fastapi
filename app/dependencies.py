"""
dependencies.py — Reusable FastAPI dependency functions.

Provides:
    get_db          → AsyncSession (database session)
    get_current_user → User (JWT-authenticated, active user)
    require_admin   → User (must have role='admin')
    get_pagination  → PaginationParams (page, page_size)
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db

http_bearer = HTTPBearer(auto_error=True)


# ── Pagination params ─────────────────────────────────────────────────────────

class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = settings.DEFAULT_PAGE_SIZE

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


async def get_pagination(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=settings.MAX_PAGE_SIZE,
        description=f"Items per page (max {settings.MAX_PAGE_SIZE})",
    ),
) -> PaginationParams:
    """
    Inject query-level pagination into any route.

    Usage:
        @router.get("/products")
        async def list_products(pagination: PaginationParams = Depends(get_pagination)):
            offset = pagination.offset
            limit  = pagination.limit
    """
    return PaginationParams(page=page, page_size=page_size)


# ── JWT helpers ───────────────────────────────────────────────────────────────

def _decode_token(token: str) -> dict:
    """
    Decode and validate a JWT.
    Raises HTTP 401 on any failure (expired, invalid signature, malformed).
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": "INVALID_TOKEN",
            "message": "Could not validate credentials. Please log in again.",
        },
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "TOKEN_EXPIRED",
                "message": "Your session has expired. Please log in again.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise credentials_exc


# ── Current user dependency ───────────────────────────────────────────────────

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Validates the Bearer JWT and returns the authenticated User ORM object.

    Raises:
        401 — token missing / invalid / expired
        401 — user not found in DB
        403 — user account deactivated

    Usage:
        @router.get("/me")
        async def me(user = Depends(get_current_user)):
            return user
    """
    # Import here to avoid circular imports at module load time
    from app.models.user import User  # noqa: PLC0415

    token = credentials.credentials
    payload = _decode_token(token)

    # Expect token type to be "access"
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_TOKEN_TYPE",
                "message": "Expected an access token.",
            },
        )

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_TOKEN",
                "message": "Token payload is missing user identifier.",
            },
        )

    # Fetch user from DB
    result = await db.execute(
        select(User).where(User.id == UUID(user_id))
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "USER_NOT_FOUND",
                "message": "The user associated with this token no longer exists.",
            },
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ACCOUNT_DEACTIVATED",
                "message": "Your account has been deactivated. Contact support.",
            },
        )

    return user


# ── Admin guard ───────────────────────────────────────────────────────────────

async def require_admin(
    current_user: Annotated[object, Depends(get_current_user)],
):
    """
    Extends get_current_user — additionally enforces role='admin'.

    Raises:
        403 — authenticated but not an admin

    Usage:
        @router.delete("/products/{id}")
        async def delete_product(admin = Depends(require_admin)):
            ...
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ADMIN_REQUIRED",
                "message": "You do not have permission to perform this action.",
            },
        )
    return current_user


# ── Optional auth (public routes that benefit from knowing the user) ──────────

async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=False))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials=credentials, db=db)
    except HTTPException:
        return None


# ── Type aliases (for cleaner route signatures) ───────────────────────────────

DBSession     = Annotated[AsyncSession, Depends(get_db)]
CurrentUser   = Annotated[object, Depends(get_current_user)]
AdminUser     = Annotated[object, Depends(require_admin)]
OptionalUser  = Annotated[object, Depends(get_optional_user)]
Pagination    = Annotated[PaginationParams, Depends(get_pagination)]