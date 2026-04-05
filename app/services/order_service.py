from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import PaginationParams
from app.models.cart import Cart, CartItem
from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.product import Product
from app.schemas.common import PaginatedResponse
from app.schemas.order import CreateOrderRequest, OrderResponse

VALID_TRANSITIONS: dict[str, list[str]] = {
    "pending":    ["confirmed", "cancelled"],
    "confirmed":  ["processing", "cancelled"],
    "processing": ["shipped", "cancelled"],
    "shipped":    ["delivered"],
    "delivered":  ["refunded"],
    "cancelled":  [],
    "refunded":   [],
}


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_order(self, order_id: UUID) -> Order | None:
        result = await self.db.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.payment),
            )
        )
        return result.scalar_one_or_none()

    async def _get_order_or_404(self, order_id: UUID) -> Order:
        order = await self._get_order(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ORDER_NOT_FOUND", "message": f"Order '{order_id}' not found."},
            )
        return order

    async def create_order(self, user_id: UUID, payload: CreateOrderRequest) -> OrderResponse:
        cart_result = await self.db.execute(
            select(Cart)
            .where(Cart.user_id == user_id)
            .options(selectinload(Cart.items).selectinload(CartItem.product))
        )
        cart = cart_result.scalar_one_or_none()

        if not cart or not cart.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "EMPTY_CART", "message": "Your cart is empty. Add items before placing an order."},
            )

        order_items = []
        total = 0

        for item in cart.items:
            product_result = await self.db.execute(
                select(Product).where(Product.id == item.product_id).with_for_update()
            )
            product = product_result.scalar_one()

            if not product.is_active:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"code": "PRODUCT_UNAVAILABLE", "message": f"'{product.name}' is no longer available."},
                )
            if product.stock_quantity < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"code": "INSUFFICIENT_STOCK", "message": f"Only {product.stock_quantity} units of '{product.name}' available."},
                )

            subtotal = product.price * item.quantity
            total += subtotal
            product.stock_quantity -= item.quantity
            self.db.add(product)

            order_items.append(OrderItem(
                product_id=product.id,
                quantity=item.quantity,
                unit_price=product.price,
                subtotal=subtotal,
            ))

        order = Order(
            user_id=user_id,
            total_amount=total,
            shipping_address=payload.shipping_address.model_dump(),
            notes=payload.notes,
        )
        self.db.add(order)
        await self.db.flush()

        for oi in order_items:
            oi.order_id = order.id
            self.db.add(oi)

        payment = Payment(order_id=order.id, method=payload.payment_method)
        self.db.add(payment)

        for item in cart.items:
            await self.db.delete(item)

        await self.db.flush()
        order = await self._get_order(order.id)
        return OrderResponse.model_validate(order)

    async def list_user_orders(self, user_id: UUID, pagination: PaginationParams) -> PaginatedResponse[OrderResponse]:
        count_result = await self.db.execute(select(func.count()).select_from(Order).where(Order.user_id == user_id))
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .options(selectinload(Order.items), selectinload(Order.payment))
            .order_by(Order.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        orders = result.scalars().all()

        return PaginatedResponse.create(
            items=[OrderResponse.model_validate(o) for o in orders],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def get_user_order_or_404(self, order_id: UUID, user_id: UUID) -> OrderResponse:
        order = await self._get_order_or_404(order_id)
        if order.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "You do not have access to this order."},
            )
        return OrderResponse.model_validate(order)

    async def cancel_order(self, order_id: UUID, user_id: UUID) -> None:
        order = await self._get_order_or_404(order_id)
        if order.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "You do not have access to this order."},
            )
        if "cancelled" not in VALID_TRANSITIONS.get(order.status, []):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "INVALID_TRANSITION", "message": f"Order in '{order.status}' status cannot be cancelled."},
            )
        order.status = "cancelled"
        self.db.add(order)
        await self.db.flush()

    async def list_all_orders(self, pagination: PaginationParams) -> PaginatedResponse[OrderResponse]:
        count_result = await self.db.execute(select(func.count()).select_from(Order))
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.payment))
            .order_by(Order.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        orders = result.scalars().all()

        return PaginatedResponse.create(
            items=[OrderResponse.model_validate(o) for o in orders],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def update_status(self, order_id: UUID, new_status: str) -> OrderResponse:
        order = await self._get_order_or_404(order_id)
        allowed = VALID_TRANSITIONS.get(order.status, [])
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "INVALID_TRANSITION",
                    "message": f"Cannot move order from '{order.status}' to '{new_status}'. Allowed: {allowed}.",
                },
            )
        order.status = new_status
        self.db.add(order)
        await self.db.flush()
        order = await self._get_order(order.id)
        return OrderResponse.model_validate(order)