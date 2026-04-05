import re
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import PaginationParams
from app.models.product import Product
from app.schemas.common import PaginatedResponse
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


class ProductService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_product_or_404(self, product_id: UUID) -> Product:
        result = await self.db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "PRODUCT_NOT_FOUND", "message": f"Product '{product_id}' not found."},
            )
        return product

    async def get_by_slug_or_404(self, slug: str) -> Product:
        result = await self.db.execute(select(Product).where(Product.slug == slug, Product.is_active == True))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "PRODUCT_NOT_FOUND", "message": f"Product with slug '{slug}' not found."},
            )
        return product

    async def _unique_slug(self, name: str, exclude_id: UUID | None = None) -> str:
        base = _slugify(name)
        slug = base
        counter = 1
        while True:
            query = select(Product).where(Product.slug == slug)
            if exclude_id:
                query = query.where(Product.id != exclude_id)
            result = await self.db.execute(query)
            if not result.scalar_one_or_none():
                return slug
            slug = f"{base}-{counter}"
            counter += 1

    async def list_products(
        self,
        pagination: PaginationParams,
        category_id: UUID | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        in_stock: bool | None = None,
        search: str | None = None,
        sort_by: str = "newest",
    ) -> PaginatedResponse[ProductResponse]:
        query = select(Product).where(Product.is_active == True)

        if category_id:
            query = query.where(Product.category_id == category_id)
        if min_price is not None:
            query = query.where(Product.price >= Decimal(str(min_price)))
        if max_price is not None:
            query = query.where(Product.price <= Decimal(str(max_price)))
        if in_stock is True:
            query = query.where(Product.stock_quantity > 0)
        if search:
            query = query.where(Product.name.ilike(f"%{search}%"))

        sort_map = {
            "price_asc": Product.price.asc(),
            "price_desc": Product.price.desc(),
            "newest": Product.created_at.desc(),
            "name": Product.name.asc(),
        }
        query = query.order_by(sort_map.get(sort_by, Product.created_at.desc()))

        total_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar_one()

        result = await self.db.execute(query.offset(pagination.offset).limit(pagination.limit))
        products = result.scalars().all()

        return PaginatedResponse.create(
            items=[ProductResponse.model_validate(p) for p in products],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def create_product(self, payload: ProductCreate) -> Product:
        sku_check = await self.db.execute(select(Product).where(Product.sku == payload.sku))
        if sku_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "SKU_EXISTS", "message": f"A product with SKU '{payload.sku}' already exists."},
            )
        slug = await self._unique_slug(payload.name)
        product = Product(**payload.model_dump(), slug=slug)
        self.db.add(product)
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def update_product(self, product_id: UUID, payload: ProductUpdate) -> Product:
        product = await self.get_product_or_404(product_id)
        data = payload.model_dump(exclude_unset=True)
        if "name" in data:
            data["slug"] = await self._unique_slug(data["name"], exclude_id=product_id)
        for field, value in data.items():
            setattr(product, field, value)
        self.db.add(product)
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def update_stock(self, product_id: UUID, stock_quantity: int) -> Product:
        product = await self.get_product_or_404(product_id)
        product.stock_quantity = stock_quantity
        self.db.add(product)
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def delete_product(self, product_id: UUID) -> None:
        product = await self.get_product_or_404(product_id)
        product.is_active = False
        self.db.add(product)
        await self.db.flush()