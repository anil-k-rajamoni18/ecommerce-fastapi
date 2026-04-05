import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AddToCartRequest(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(ge=1, le=100)


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(ge=1, le=100)


class CartItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    product_image: str | None
    unit_price: Decimal
    quantity: int
    subtotal: Decimal


class CartResponse(BaseModel):
    id: uuid.UUID
    items: list[CartItemResponse]
    total_items: int
    total_amount: Decimal