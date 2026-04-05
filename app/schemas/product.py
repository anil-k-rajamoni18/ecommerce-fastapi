import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProductCreate(BaseModel):
    category_id: uuid.UUID
    name: str = Field(min_length=3, max_length=255, strip_whitespace=True)
    description: str | None = Field(default=None, max_length=5000)
    price: Decimal = Field(gt=0, decimal_places=2)
    compare_price: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    stock_quantity: int = Field(ge=0)
    sku: str = Field(min_length=3, max_length=100, strip_whitespace=True)
    image_url: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def compare_price_must_exceed_price(self) -> "ProductCreate":
        if self.compare_price is not None and self.compare_price <= self.price:
            raise ValueError("compare_price must be greater than price")
        return self


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    compare_price: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    stock_quantity: int | None = Field(default=None, ge=0)
    image_url: str | None = None
    is_active: bool | None = None


class StockUpdateRequest(BaseModel):
    stock_quantity: int = Field(ge=0)


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_id: uuid.UUID
    name: str
    slug: str
    description: str | None
    price: Decimal
    compare_price: Decimal | None
    stock_quantity: int
    sku: str
    image_url: str | None
    is_active: bool
    created_at: datetime


class ProductFilterParams(BaseModel):
    category_id: uuid.UUID | None = None
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    in_stock: bool | None = None
    search: str | None = Field(default=None, max_length=100)
    sort_by: Literal["price_asc", "price_desc", "newest", "name"] = "newest"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def max_price_gte_min_price(self) -> "ProductFilterParams":
        if self.min_price is not None and self.max_price is not None:
            if self.max_price < self.min_price:
                raise ValueError("max_price must be greater than or equal to min_price")
        return self