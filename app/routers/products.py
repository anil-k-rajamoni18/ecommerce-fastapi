import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import AdminUser, Pagination
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.product import (
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    StockUpdateRequest,
)
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/", response_model=PaginatedResponse[ProductResponse])
async def list_products(
    pagination: Pagination,
    db: AsyncSession = Depends(get_db),
    category_id: uuid.UUID | None = Query(default=None),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    in_stock: bool | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    sort_by: Literal["price_asc", "price_desc", "newest", "name"] = Query(default="newest"),
):
    return await ProductService(db).list_products(
        pagination=pagination,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
        search=search,
        sort_by=sort_by,
    )


@router.get("/slug/{slug}", response_model=ProductResponse)
async def get_product_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    return await ProductService(db).get_by_slug_or_404(slug)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await ProductService(db).get_product_or_404(product_id)


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(payload: ProductCreate, admin: AdminUser, db: AsyncSession = Depends(get_db)):
    return await ProductService(db).create_product(payload)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: uuid.UUID, payload: ProductUpdate, admin: AdminUser, db: AsyncSession = Depends(get_db)):
    return await ProductService(db).update_product(product_id, payload)


@router.patch("/{product_id}/stock", response_model=ProductResponse)
async def update_stock(product_id: uuid.UUID, payload: StockUpdateRequest, admin: AdminUser, db: AsyncSession = Depends(get_db)):
    return await ProductService(db).update_stock(product_id, payload.stock_quantity)


@router.delete("/{product_id}", response_model=MessageResponse)
async def delete_product(product_id: uuid.UUID, admin: AdminUser, db: AsyncSession = Depends(get_db)):
    await ProductService(db).delete_product(product_id)
    return MessageResponse(message="Product deleted successfully")