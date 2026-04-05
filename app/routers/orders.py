import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import AdminUser, CurrentUser, Pagination
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.order import CreateOrderRequest, OrderResponse, UpdateOrderStatusRequest
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


# ── Customer routes ───────────────────────────────────────────────────────────

@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(payload: CreateOrderRequest, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await OrderService(db).create_order(current_user.id, payload)


@router.get("/", response_model=PaginatedResponse[OrderResponse])
async def list_my_orders(current_user: CurrentUser, pagination: Pagination, db: AsyncSession = Depends(get_db)):
    return await OrderService(db).list_user_orders(current_user.id, pagination)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_my_order(order_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await OrderService(db).get_user_order_or_404(order_id, current_user.id)


@router.post("/{order_id}/cancel", response_model=MessageResponse)
async def cancel_order(order_id: uuid.UUID, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    await OrderService(db).cancel_order(order_id, current_user.id)
    return MessageResponse(message="Order cancelled successfully")


# ── Admin routes ──────────────────────────────────────────────────────────────

@router.get("/admin/all", response_model=PaginatedResponse[OrderResponse])
async def list_all_orders(admin: AdminUser, pagination: Pagination, db: AsyncSession = Depends(get_db)):
    return await OrderService(db).list_all_orders(pagination)


@router.patch("/admin/{order_id}/status", response_model=OrderResponse)
async def update_order_status(order_id: uuid.UUID, payload: UpdateOrderStatusRequest, admin: AdminUser, db: AsyncSession = Depends(get_db)):
    return await OrderService(db).update_status(order_id, payload.status)