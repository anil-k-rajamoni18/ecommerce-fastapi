import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser
from app.schemas.cart import AddToCartRequest, CartResponse, UpdateCartItemRequest
from app.schemas.common import MessageResponse
from app.services.cart_service import CartService

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("/", response_model=CartResponse)
async def get_cart(current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await CartService(db).get_or_create_cart(current_user.id)


@router.post("/items", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
async def add_item(payload: AddToCartRequest, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await CartService(db).add_item(current_user.id, payload)


@router.patch("/items/{item_id}", response_model=CartResponse)
async def update_item(item_id: uuid.UUID, payload: UpdateCartItemRequest, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await CartService(db).update_item(current_user.id, item_id, payload.quantity)


@router.delete("/items/{item_id}", response_model=CartResponse)
async def remove_item(item_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await CartService(db).remove_item(current_user.id, item_id)


@router.delete("/", response_model=MessageResponse)
async def clear_cart(current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    await CartService(db).clear_cart(current_user.id)
    return MessageResponse(message="Cart cleared successfully")