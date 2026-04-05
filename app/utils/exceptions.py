from fastapi import HTTPException, status


def _exc(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


# ── 400 Bad Request ───────────────────────────────────────────────────────────

def empty_cart_error() -> HTTPException:
    return _exc(status.HTTP_400_BAD_REQUEST, "EMPTY_CART", "Cart is empty. Add items before placing an order.")


def wrong_password_error() -> HTTPException:
    return _exc(status.HTTP_400_BAD_REQUEST, "WRONG_PASSWORD", "Current password is incorrect.")


# ── 401 Unauthorized ──────────────────────────────────────────────────────────

def invalid_credentials_error() -> HTTPException:
    return _exc(status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS", "Incorrect email or password.")


def token_expired_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "TOKEN_EXPIRED", "message": "Token has expired. Please log in again."},
        headers={"WWW-Authenticate": "Bearer"},
    )


def invalid_token_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "INVALID_TOKEN", "message": "Could not validate token."},
        headers={"WWW-Authenticate": "Bearer"},
    )


# ── 403 Forbidden ─────────────────────────────────────────────────────────────

def forbidden_error(message: str = "You do not have permission to perform this action.") -> HTTPException:
    return _exc(status.HTTP_403_FORBIDDEN, "FORBIDDEN", message)


def admin_required_error() -> HTTPException:
    return _exc(status.HTTP_403_FORBIDDEN, "ADMIN_REQUIRED", "Admin access required.")


def account_deactivated_error() -> HTTPException:
    return _exc(status.HTTP_403_FORBIDDEN, "ACCOUNT_DEACTIVATED", "Your account has been deactivated. Contact support.")


# ── 404 Not Found ─────────────────────────────────────────────────────────────

def user_not_found_error(identifier: str = "") -> HTTPException:
    msg = f"User '{identifier}' not found." if identifier else "User not found."
    return _exc(status.HTTP_404_NOT_FOUND, "USER_NOT_FOUND", msg)


def product_not_found_error(identifier: str = "") -> HTTPException:
    msg = f"Product '{identifier}' not found." if identifier else "Product not found."
    return _exc(status.HTTP_404_NOT_FOUND, "PRODUCT_NOT_FOUND", msg)


def category_not_found_error(identifier: str = "") -> HTTPException:
    msg = f"Category '{identifier}' not found." if identifier else "Category not found."
    return _exc(status.HTTP_404_NOT_FOUND, "CATEGORY_NOT_FOUND", msg)


def order_not_found_error(identifier: str = "") -> HTTPException:
    msg = f"Order '{identifier}' not found." if identifier else "Order not found."
    return _exc(status.HTTP_404_NOT_FOUND, "ORDER_NOT_FOUND", msg)


def cart_not_found_error() -> HTTPException:
    return _exc(status.HTTP_404_NOT_FOUND, "CART_NOT_FOUND", "Cart not found.")


def cart_item_not_found_error() -> HTTPException:
    return _exc(status.HTTP_404_NOT_FOUND, "ITEM_NOT_FOUND", "Cart item not found.")


# ── 409 Conflict ──────────────────────────────────────────────────────────────

def email_exists_error() -> HTTPException:
    return _exc(status.HTTP_409_CONFLICT, "EMAIL_ALREADY_EXISTS", "An account with this email already exists.")


def sku_exists_error(sku: str) -> HTTPException:
    return _exc(status.HTTP_409_CONFLICT, "SKU_EXISTS", f"A product with SKU '{sku}' already exists.")


def insufficient_stock_error(product_name: str, available: int) -> HTTPException:
    return _exc(status.HTTP_409_CONFLICT, "INSUFFICIENT_STOCK", f"Only {available} units of '{product_name}' available.")


def product_unavailable_error(product_name: str) -> HTTPException:
    return _exc(status.HTTP_409_CONFLICT, "PRODUCT_UNAVAILABLE", f"'{product_name}' is no longer available.")


def invalid_status_transition_error(current: str, requested: str, allowed: list[str]) -> HTTPException:
    return _exc(
        status.HTTP_409_CONFLICT,
        "INVALID_TRANSITION",
        f"Cannot move order from '{current}' to '{requested}'. Allowed transitions: {allowed}.",
    )