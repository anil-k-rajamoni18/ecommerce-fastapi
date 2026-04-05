from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import PaginationParams
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.user import AdminUserUpdateRequest, UserResponse


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_or_404(self, user_id: UUID) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "USER_NOT_FOUND", "message": f"User '{user_id}' not found."},
            )
        return user

    async def list_users(self, pagination: PaginationParams) -> PaginatedResponse[UserResponse]:
        total_result = await self.db.execute(select(func.count()).select_from(User))
        total = total_result.scalar_one()

        result = await self.db.execute(
            select(User).order_by(User.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
        )
        users = result.scalars().all()

        return PaginatedResponse.create(
            items=[UserResponse.model_validate(u) for u in users],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def admin_update_user(self, user_id: UUID, payload: AdminUserUpdateRequest) -> User:
        user = await self.get_user_or_404(user_id)
        if payload.is_active is not None:
            user.is_active = payload.is_active
        if payload.role is not None:
            user.role = payload.role
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def deactivate_user(self, user_id: UUID) -> None:
        user = await self.get_user_or_404(user_id)
        user.is_active = False
        self.db.add(user)
        await self.db.flush()