import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ShippingAddress(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    phone: str = Field(pattern=r"^\+?[1-9]\d{9,14}$")
    address_line1: str = Field(min_length=5, max_length=255)
    address_line2: str | None = None
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    pincode: str = Field(pattern=r"^\d{6}$")
    country: str = Field(default="India", max_length=100)


class CreateOrderRequest(BaseModel):
    shipping_address: ShippingAddress
    payment_method: Literal["cod", "upi", "card", "netbanking"]
    notes: str | None = Field(default=None, max_length=500)


class UpdateOrderStatusRequest(BaseModel):
    status: Literal["confirmed", "processing", "shipped", "delivered", "cancelled", "refunded"]


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    method: str
    status: str
    transaction_id: str | None
    paid_at: datetime | None


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    total_amount: Decimal
    shipping_address: dict
    notes: str | None
    items: list[OrderItemResponse]
    payment: PaymentResponse | None
    created_at: datetime