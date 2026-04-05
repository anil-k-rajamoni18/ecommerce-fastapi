# 🛒 E-Commerce API

A production-grade REST API built with **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.0 (async)**, and **JWT authentication**. Designed for a 1-day build with clean layered architecture.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.111+ |
| Language | Python 3.12 |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Database | PostgreSQL 16 |
| Validation | Pydantic v2 |
| Auth | JWT (python-jose) + bcrypt |
| Server | Uvicorn + Gunicorn |
| Package Manager | Poetry |
| Deployment | Render.com |

---

## Project Structure

```
ecommerce-api/
├── app/
│   ├── main.py               # App entry point, lifespan, routers
│   ├── config.py             # Settings via pydantic-settings
│   ├── database.py           # SQLAlchemy async engine + session
│   ├── dependencies.py       # get_db, get_current_user, require_admin
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── category.py
│   │   ├── product.py
│   │   ├── cart.py
│   │   ├── order.py
│   │   └── payment.py
│   ├── schemas/              # Pydantic v2 request/response schemas
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── category.py
│   │   ├── product.py
│   │   ├── cart.py
│   │   ├── order.py
│   │   └── common.py
│   ├── routers/              # FastAPI route handlers
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── categories.py
│   │   ├── products.py
│   │   ├── cart.py
│   │   └── orders.py
│   ├── services/             # Business logic
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── category_service.py
│   │   ├── product_service.py
│   │   ├── cart_service.py
│   │   └── order_service.py
│   ├── repositories/         # DB query layer
│   │   ├── user_repo.py
│   │   ├── product_repo.py
│   │   ├── cart_repo.py
│   │   └── order_repo.py
│   └── utils/
│       ├── security.py
│       ├── pagination.py
│       └── exceptions.py
├── alembic/
│   ├── env.py
│   └── versions/
├── tests/
├── .env.example
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── render.yaml
└── pyproject.toml
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL 16
- Poetry

### 1. Clone & Install

```bash
git clone https://github.com/your-username/ecommerce-api.git
cd ecommerce-api
poetry install
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
APP_NAME=ECommerceAPI
DEBUG=true
SECRET_KEY=your-super-secret-key-minimum-32-characters-long

DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/ecommerce_db

ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

ALLOWED_ORIGINS=["http://localhost:3000"]
DEFAULT_PAGE_SIZE=20
MAX_PAGE_SIZE=100
```

### 3. Create Database

```bash
# Using psql
psql -U postgres -c "CREATE DATABASE ecommerce_db;"
```

### 4. Run Migrations

```bash
poetry run alembic revision --autogenerate -m "initial_schema"
poetry run alembic upgrade head
```

### 5. Start the Server

```bash
poetry run uvicorn app.main:app --reload
```

API is now live at `http://127.0.0.1:8000`

---

## API Docs

| URL | Description |
|---|---|
| `http://127.0.0.1:8000/api/v1/docs` | Swagger UI |
| `http://127.0.0.1:8000/api/v1/redoc` | ReDoc |
| `http://127.0.0.1:8000/api/v1/health` | Health check |

---

## Authentication

The API uses **JWT Bearer tokens**.

### Register

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "Secret@123",
  "full_name": "John Doe"
}
```

Password rules: min 8 chars, 1 uppercase, 1 digit, 1 special character (`!@#$%^&*`).

### Login

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "Secret@123"
}
```

Response:

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Using the Token

```http
GET /api/v1/auth/me
Authorization: Bearer eyJ...
```

**In Swagger UI** — click the 🔒 **Authorize** button, paste your `access_token`, click Authorize.

---

## API Endpoints

### Auth — `/api/v1/auth`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/register` | Public | Register new account |
| POST | `/login` | Public | Login, get tokens |
| POST | `/refresh` | Public | Refresh access token |
| POST | `/logout` | Bearer | Logout |
| GET | `/me` | Bearer | Get own profile |
| PATCH | `/me` | Bearer | Update own profile |
| POST | `/me/change-password` | Bearer | Change password |

### Categories — `/api/v1/categories`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/` | Public | List all categories (with children) |
| GET | `/{category_id}` | Public | Get category |
| POST | `/` | Admin | Create category |
| PATCH | `/{category_id}` | Admin | Update category |
| DELETE | `/{category_id}` | Admin | Soft delete category |

### Products — `/api/v1/products`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/` | Public | List products (paginated + filtered) |
| GET | `/{product_id}` | Public | Get product |
| GET | `/slug/{slug}` | Public | Get product by slug |
| POST | `/` | Admin | Create product |
| PATCH | `/{product_id}` | Admin | Update product |
| PATCH | `/{product_id}/stock` | Admin | Update stock |
| DELETE | `/{product_id}` | Admin | Soft delete product |

**Product filters** (query params):

```
?category_id=uuid&min_price=100&max_price=5000
&in_stock=true&search=laptop&sort_by=price_asc
&page=1&page_size=20
```

`sort_by` options: `price_asc`, `price_desc`, `newest`, `name`

### Cart — `/api/v1/cart`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/` | Bearer | Get cart |
| POST | `/items` | Bearer | Add item |
| PATCH | `/items/{item_id}` | Bearer | Update quantity |
| DELETE | `/items/{item_id}` | Bearer | Remove item |
| DELETE | `/` | Bearer | Clear cart |

### Orders — `/api/v1/orders`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/` | Bearer | Place order from cart |
| GET | `/` | Bearer | List own orders |
| GET | `/{order_id}` | Bearer | Get own order |
| POST | `/{order_id}/cancel` | Bearer | Cancel order |
| GET | `/admin/all` | Admin | List all orders |
| PATCH | `/admin/{order_id}/status` | Admin | Update order status |

**Order status flow:**

```
pending → confirmed → processing → shipped → delivered
                    ↘ cancelled
                                            ↘ refunded
```

### Users — `/api/v1/users` (Admin only)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/` | Admin | List all users |
| GET | `/{user_id}` | Admin | Get user |
| PATCH | `/{user_id}` | Admin | Update role / status |
| DELETE | `/{user_id}` | Admin | Deactivate user |

---

## Request & Response Examples

### Create Product (Admin)

```http
POST /api/v1/products
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "category_id": "uuid-here",
  "name": "MacBook Pro 14",
  "description": "Apple M3 chip, 16GB RAM",
  "price": 149999.00,
  "compare_price": 159999.00,
  "stock_quantity": 50,
  "sku": "MBP-14-M3-2024",
  "image_url": "https://example.com/macbook.jpg"
}
```

### Place Order

```http
POST /api/v1/orders
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "shipping_address": {
    "full_name": "John Doe",
    "phone": "+919876543210",
    "address_line1": "123 MG Road",
    "city": "Hyderabad",
    "state": "Telangana",
    "pincode": "500001",
    "country": "India"
  },
  "payment_method": "upi",
  "notes": "Leave at door"
}
```

### Paginated Response Format

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5,
  "has_next": true,
  "has_prev": false
}
```

### Error Response Format

```json
{
  "error": "PRODUCT_NOT_FOUND",
  "message": "Product 'abc-123' not found.",
  "details": null
}
```

---

## Database Schema

```
users ──────────< orders ──────────< order_items >────── products
users ──────────< carts  ──────────< cart_items  >────── products
orders ─────────< payments
categories ──────< products
categories ──────< categories (self-ref parent/children)
```

---

## Docker (Local Dev)

```bash
docker-compose up --build
```

Services:
- API → `http://localhost:8000`
- PostgreSQL → `localhost:5432`

---

## Deployment on Render.com

1. Push code to GitHub
2. Go to [render.com](https://render.com) → **New** → **Blueprint**
3. Connect your GitHub repo — Render reads `render.yaml` automatically
4. Set environment variables in the Render dashboard:
   - `SECRET_KEY` → generate a strong random string
5. Deploy — your API will be live at `https://your-app.onrender.com`

> **Note:** Free tier on Render spins down after 15 minutes of inactivity. First request after sleep takes ~30 seconds.

---

## Running Tests

```bash
poetry run pytest tests/ -v --asyncio-mode=auto
```

With coverage:

```bash
poetry run pytest tests/ -v --asyncio-mode=auto --cov=app --cov-report=html
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | ✅ | — | JWT signing key (min 32 chars) |
| `DATABASE_URL` | ✅ | — | PostgreSQL async connection string |
| `DEBUG` | ❌ | `false` | Enable SQL logging |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ❌ | `30` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | ❌ | `7` | Refresh token TTL |
| `ALLOWED_ORIGINS` | ❌ | `[]` | CORS allowed origins (JSON array) |
| `DEFAULT_PAGE_SIZE` | ❌ | `20` | Default pagination size |
| `MAX_PAGE_SIZE` | ❌ | `100` | Max pagination size |

---

## Common Errors

| Error Code | Status | Cause |
|---|---|---|
| `INVALID_CREDENTIALS` | 401 | Wrong email or password |
| `TOKEN_EXPIRED` | 401 | Access token expired — use `/auth/refresh` |
| `INVALID_TOKEN` | 401 | Malformed or tampered token |
| `ADMIN_REQUIRED` | 403 | Route requires admin role |
| `ACCOUNT_DEACTIVATED` | 403 | User account is inactive |
| `USER_NOT_FOUND` | 404 | User does not exist |
| `PRODUCT_NOT_FOUND` | 404 | Product does not exist or is inactive |
| `ORDER_NOT_FOUND` | 404 | Order does not exist |
| `EMAIL_ALREADY_EXISTS` | 409 | Email already registered |
| `INSUFFICIENT_STOCK` | 409 | Not enough stock for requested quantity |
| `EMPTY_CART` | 400 | Tried to order with empty cart |
| `INVALID_TRANSITION` | 409 | Invalid order status change |
| `VALIDATION_ERROR` | 422 | Request body failed schema validation |

---

## License

MIT