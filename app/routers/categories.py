import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import AdminUser
from app.schemas.category import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    CategoryWithChildrenResponse,
)
from app.schemas.common import MessageResponse
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("/", response_model=list[CategoryWithChildrenResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    return await CategoryService(db).list_categories()


@router.get("/{category_id}", response_model=CategoryWithChildrenResponse)
async def get_category(category_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await CategoryService(db).get_category_or_404(category_id)


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(payload: CategoryCreate, admin: AdminUser, db: AsyncSession = Depends(get_db)):
    return await CategoryService(db).create_category(payload)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(category_id: uuid.UUID, payload: CategoryUpdate, admin: AdminUser, db: AsyncSession = Depends(get_db)):
    return await CategoryService(db).update_category(category_id, payload)


@router.delete("/{category_id}", response_model=MessageResponse)
async def delete_category(category_id: uuid.UUID, admin: AdminUser, db: AsyncSession = Depends(get_db)):
    await CategoryService(db).delete_category(category_id)
    return MessageResponse(message="Category deleted successfully")