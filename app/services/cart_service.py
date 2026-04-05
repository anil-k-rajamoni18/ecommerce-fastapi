from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.schemas.cart import AddToCartRequest, CartItemResponse, CartResponse


class CartService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_cart(self, user_id: UUID) -> Cart | None:
        result = await self.db.execute(
            select(Cart)
            .where(Cart.user_id == user_id)
            .options(selectinload(Cart.items).selectinload(CartItem.product))
        )
        return result.scalar_one_or_none()

    async def get_or_create_cart(self, user_id: UUID) -> CartResponse:
        cart = await self._get_cart(user_id)
        if not cart:
            cart = Cart(user_id=user_id)
            self.db.add(cart)
            await self.db.flush()
            await self.db.refresh(cart)
            cart.items = []
        return self._build_response(cart)

    async def add_item(self, user_id: UUID, payload: AddToCartRequest) -> CartResponse:
        product_result = await self.db.execute(
            select(Product).where(Product.id == payload.product_id, Product.is_active == True)
        )
        product = product_result.scalar_one_or_none()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "PRODUCT_NOT_FOUND", "message": "Product not found or inactive."},
            )
        if product.stock_quantity < payload.quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "INSUFFICIENT_STOCK", "message": f"Only {product.stock_quantity} units available."},
            )

        cart = await self._get_cart(user_id)
        if not cart:
            cart = Cart(user_id=user_id)
            self.db.add(cart)
            await self.db.flush()
            await self.db.refresh(cart)

        existing_result = await self.db.execute(
            select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == payload.product_id)
        )
        existing = existing_result.scalar_one_or_none()

        if existing:
            new_qty = existing.quantity + payload.quantity
            if product.stock_quantity < new_qty:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"code": "INSUFFICIENT_STOCK", "message": f"Only {product.stock_quantity} units available."},
                )
            existing.quantity = new_qty
            self.db.add(existing)
        else:
            self.db.add(CartItem(cart_id=cart.id, product_id=payload.product_id, quantity=payload.quantity))

        await self.db.flush()
        cart = await self._get_cart(user_id)
        return self._build_response(cart)

    async def update_item(self, user_id: UUID, item_id: UUID, quantity: int) -> CartResponse:
        cart = await self._get_cart(user_id)
        if not cart:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "CART_NOT_FOUND", "message": "Cart not found."})

        item = next((i for i in cart.items if i.id == item_id), None)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "ITEM_NOT_FOUND", "message": "Cart item not found."})

        if item.product.stock_quantity < quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "INSUFFICIENT_STOCK", "message": f"Only {item.product.stock_quantity} units available."},
            )

        item.quantity = quantity
        self.db.add(item)
        await self.db.flush()
        cart = await self._get_cart(user_id)
        return self._build_response(cart)

    async def remove_item(self, user_id: UUID, item_id: UUID) -> CartResponse:
        cart = await self._get_cart(user_id)
        if not cart:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "CART_NOT_FOUND", "message": "Cart not found."})

        item = next((i for i in cart.items if i.id == item_id), None)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "ITEM_NOT_FOUND", "message": "Cart item not found."})

        await self.db.delete(item)
        await self.db.flush()
        cart = await self._get_cart(user_id)
        return self._build_response(cart)

    async def clear_cart(self, user_id: UUID) -> None:
        cart = await self._get_cart(user_id)
        if cart:
            for item in cart.items:
                await self.db.delete(item)
            await self.db.flush()

    def _build_response(self, cart: Cart) -> CartResponse:
        items = []
        for item in cart.items:
            p = item.product
            subtotal = p.price * item.quantity
            items.append(CartItemResponse(
                id=item.id,
                product_id=p.id,
                product_name=p.name,
                product_image=p.image_url,
                unit_price=p.price,
                quantity=item.quantity,
                subtotal=subtotal,
            ))
        total_amount = sum(i.subtotal for i in items) if items else Decimal("0.00")
        return CartResponse(
            id=cart.id,
            items=items,
            total_items=sum(i.quantity for i in items),
            total_amount=total_amount,
        )