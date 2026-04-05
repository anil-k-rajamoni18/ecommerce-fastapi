import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.utils.exceptions import category_not_found_error, _exc
from fastapi import status


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


class CategoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_with_children(self, category_id: UUID) -> Category | None:
        result = await self.db.execute(
            select(Category)
            .where(Category.id == category_id)
            .options(selectinload(Category.children))
        )
        return result.scalar_one_or_none()

    async def _unique_slug(self, name: str, exclude_id: UUID | None = None) -> str:
        base = _slugify(name)
        slug, counter = base, 1
        while True:
            query = select(Category).where(Category.slug == slug)
            if exclude_id:
                query = query.where(Category.id != exclude_id)
            if not (await self.db.execute(query)).scalar_one_or_none():
                return slug
            slug = f"{base}-{counter}"
            counter += 1

    async def get_category_or_404(self, category_id: UUID) -> Category:
        category = await self._get_with_children(category_id)
        if not category:
            raise category_not_found_error(str(category_id))
        return category

    async def list_categories(self) -> list[Category]:
        result = await self.db.execute(
            select(Category)
            .where(Category.is_active == True, Category.parent_id == None)
            .options(selectinload(Category.children))
            .order_by(Category.name.asc())
        )
        return result.scalars().all()

    async def create_category(self, payload) -> Category:
        name_check = await self.db.execute(
            select(Category).where(Category.name == payload.name)
        )
        if name_check.scalar_one_or_none():
            raise _exc(status.HTTP_409_CONFLICT, "CATEGORY_EXISTS", f"Category '{payload.name}' already exists.")

        if payload.parent_id:
            parent = await self._get_with_children(payload.parent_id)
            if not parent:
                raise category_not_found_error(str(payload.parent_id))

        slug = await self._unique_slug(payload.name)
        category = Category(
            name=payload.name,
            slug=slug,
            description=payload.description,
            parent_id=payload.parent_id,
        )
        self.db.add(category)
        await self.db.flush()
        return await self._get_with_children(category.id)

    async def update_category(self, category_id: UUID, payload) -> Category:
        category = await self.get_category_or_404(category_id)
        data = payload.model_dump(exclude_unset=True)

        if "name" in data and data["name"] != category.name:
            dupe = (await self.db.execute(
                select(Category).where(Category.name == data["name"], Category.id != category_id)
            )).scalar_one_or_none()
            if dupe:
                raise _exc(status.HTTP_409_CONFLICT, "CATEGORY_EXISTS", f"Category '{data['name']}' already exists.")
            data["slug"] = await self._unique_slug(data["name"], exclude_id=category_id)

        if "parent_id" in data and data["parent_id"]:
            if data["parent_id"] == category_id:
                raise _exc(status.HTTP_400_BAD_REQUEST, "INVALID_PARENT", "A category cannot be its own parent.")
            parent = await self._get_with_children(data["parent_id"])
            if not parent:
                raise category_not_found_error(str(data["parent_id"]))

        for field, value in data.items():
            setattr(category, field, value)

        self.db.add(category)
        await self.db.flush()
        return await self._get_with_children(category_id)

    async def delete_category(self, category_id: UUID) -> None:
        category = await self.get_category_or_404(category_id)
        category.is_active = False
        self.db.add(category)
        await self.db.flush()