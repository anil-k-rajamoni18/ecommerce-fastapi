import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import AdminUser, Pagination
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.user import AdminUserUpdateRequest, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def list_users(admin: AdminUser, pagination: Pagination, db: AsyncSession = Depends(get_db)):
    return await UserService(db).list_users(pagination)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: uuid.UUID, admin: AdminUser, db: AsyncSession = Depends(get_db)):
    return await UserService(db).get_user_or_404(user_id)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(user_id: uuid.UUID, payload: AdminUserUpdateRequest, admin: AdminUser, db: AsyncSession = Depends(get_db)):
    return await UserService(db).admin_update_user(user_id, payload)


@router.delete("/{user_id}", response_model=MessageResponse)
async def deactivate_user(user_id: uuid.UUID, admin: AdminUser, db: AsyncSession = Depends(get_db)):
    await UserService(db).deactivate_user(user_id)
    return MessageResponse(message="User deactivated successfully")