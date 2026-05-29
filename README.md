# Speedpay Wallet

**A fintech backend for handling user registration, authentication, account management, and payments.**

---

##  Quick Start (Local Development)

1. **Clone the repository**
   ```bash
   git clone https://github.com/Oguntayo/speedpay_wallet.git
   cd speedpay_wallet
   ```

2. **Create a virtual environment & install dependencies**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   - Copy the example file:
     ```bash
     cp .example.env .env
     ```
   - Edit ``.env`` and set the values you need (see the comments inside the file).  The most important ones are:
     - `SECRET_KEY`
     - `ENVIRONMENT=DEVELOPMENT`  _(or `PRODUCTION` for prod mode)_
     - `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`
     - Database URL (`DATABASE_URL` – defaults to SQLite for dev)
     - JWT lifetimes

4. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

5. **Start the development server**
   ```bash
   python manage.py runserver
   ```
   The API will be available at **http://127.0.0.1:8000/**.

5. **Run the test suite** (optional, but highly recommended before any change)
   ```bash
   python manage.py test
   ```

---

## Environment‑Based Settings

The project uses three settings modules:
- `speedpay_project/settings.py` – base settings.
- `speedpay_project/dev.py` – imported when `ENVIRONMENT=DEVELOPMENT` (debug on, `ALLOWED_HOSTS=['*']`).
- `speedpay_project/prod.py` – imported when `ENVIRONMENT=PRODUCTION` (debug off, values read from ``.env``).

The **manage.py** script automatically selects the proper module:
```python
env = os.getenv('ENVIRONMENT', 'DEVELOPMENT').upper()
settings_module = f"speedpay_project.{ 'dev' if env == 'DEVELOPMENT' else 'prod' }"
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)
```

---

## API Endpoints

| Method | Path | Description | Payload | Response |
|--------|------|-------------|---------|----------|
| **POST** | `/api/auth/register/` | Register a new user (strong password validation). | `{ "email": "user@example.com", "password": "StrongPass123!", "first_name": "John", "last_name": "Doe", "user_type": "customer" }` | `201 Created` – `{ "id": "<uuid>", "email": "user@example.com", "first_name": "John", "last_name": "Doe", "user_type": "customer" }` |
| **POST** | `/api/auth/login/` | Obtain JWT tokens. | `{ "email": "user@example.com", "password": "StrongPass123!" }` | `200 OK` – `{ "access": "<jwt>", "refresh": "<jwt>", "user": { "id": "<uuid>", "email": "user@example.com", "first_name": "John", "last_name": "Doe", "user_type": "customer", "balance": "0.00" } }` |
| **POST** | `/api/auth/token/refresh/` | Refresh JWT token. | `{ "refresh": "<refresh_token>" }` | `200 OK` – `{ "access": "<new_jwt>" }` |
| **GET**  | `/api/auth/me/` | Retrieve the authenticated user profile. | N/A | `200 OK` – `{ "id": "<uuid>", "email": "user@example.com", "first_name": "John", "last_name": "Doe", "user_type": "customer", "balance": "0.00" }` |
| **POST** | `/api/auth/change-password/` | Change password (old → new). | `{ "old_password": "OldPass123!", "new_password": "NewPass123!" }` | `200 OK` – `{ "detail": "Password changed successfully." }` |
| **POST** | `/api/auth/forgot-password/` | Initiate password‑reset flow. | `{ "email": "user@example.com" }` | `200 OK` – `{ "detail": "Password reset email sent if the account exists." }` |
| **POST** | `/api/auth/reset-password/` | Complete password reset using token. | `{ "token": "<reset_token>", "new_password": "NewPass123!" }` | `200 OK` – `{ "detail": "Password has been reset successfully." }` |
| **GET**  | `/api/payment/balance/` | Get current account balance. | N/A | `200 OK` – `{ "account_number": "123456", "balance": "1500.00", "name": "John Doe" }` |
| **POST** | `/api/payment/deposit/` | Deposit funds into own account. | `{ "amount": "100.00" }` | `200 OK` – `{ "detail": "Deposit successful.", "balance": "1600.00" }` |
| **POST** | `/api/payment/withdraw/` | Withdraw funds from own account. | `{ "amount": "100.00" }` | `200 OK` – `{ "detail": "Withdrawal successful.", "balance": "1400.00" }` |
| **POST** | `/api/payment/transfer/` | Transfer funds – requires `destination_account` and `destination_name`. | `{ "amount": "100.00", "destination_account": "654321", "destination_name": "Jane Smith" }` | `200 OK` – `{ "detail": "Transfer successful.", "balance": "1300.00" }` |
| **POST** | `/api/payment/account-name/` | Provide `account_number` and receive the holder’s full name. | `{ "account_number": "654321" }` | `200 OK` – `{ "account_number": "654321", "name": "Jane Smith" }` |
| **GET**  | `/api/payment/transactions/` | List transaction history (paginated, filterable). | N/A (query params) | `200 OK` – `{ "count": 12, "next": "...", "previous": null, "results": [{ "id": "<uuid>", "transaction_type": "deposit", "amount": "100.00", "balance_after": "1500.00", "description": "", "created_at": "2026-05-29T14:00:00Z" }, …] }` |
| **GET**  | `/api/user/users/` | **Admin only** – List all users with their account numbers and balances (paginated). | N/A | `200 OK` – `{ "count": 5, "next": null, "previous": null, "results": [{ "id": "<uuid>", "email": "admin@example.com", "first_name": "Admin", "last_name": "User", "user_type": "admin", "account_number": null, "balance": null }, { "id": "<uuid>", "email": "cust@example.com", "first_name": "John", "last_name": "Doe", "user_type": "customer", "account_number": "123456", "balance": "1300.00" }, …] }` |
| **All endpoints require JWT authentication (`IsAuthenticated`). The `UserListView` (`/api/user/users/`) is restricted to users with `user_type == "admin"`. |

---

## LIVE URL FOR THE SWAGGER DOCS
- https://speedpay-wallet.onrender.com/api/schema/swagger-ui/#
---
