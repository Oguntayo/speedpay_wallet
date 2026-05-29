# Speedpay Wallet

**A fintech backend for handling user registration, authentication, account management, and payments.**

---

## 📦 Quick Start (Local Development)

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
     - JWT lifetimes, email backend, etc.

4. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create a super‑user (optional, for admin UI)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Start the development server**
   ```bash
   python manage.py runserver
   ```
   The API will be available at **http://127.0.0.1:8000/**.

7. **Run the test suite** (optional, but highly recommended before any change)
   ```bash
   python manage.py test
   ```

---

## ⚙️ Environment‑Based Settings

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

## 📚 API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| **POST** | `/api/auth/register/` | Register a new user (strong password validation). |
| **POST** | `/api/auth/login/` | Obtain JWT tokens, response now includes `user_type`. |
| **POST** | `/api/auth/token/refresh/` | Refresh JWT token. |
| **GET**  | `/api/auth/me/` | Retrieve the authenticated user profile. |
| **POST** | `/api/auth/change-password/` | Change password (old → new). |
| **POST** | `/api/auth/forgot-password/` | Initiate password‑reset flow (no email enumeration). |
| **POST** | `/api/auth/reset-password/` | Complete password reset using token. |
| **GET**  | `/api/payment/balance/` | Get current account balance (auth required). |
| **POST** | `/api/payment/deposit/` | Deposit funds into own account. |
| **POST** | `/api/payment/withdraw/` | Withdraw funds from own account. |
| **POST** | `/api/payment/transfer/` | Transfer funds – accepts `destination_account` **or** `destination_name` (full name). |
| **POST** | `/api/payment/account-name/` | **New** – Provide `account_number` and receive the holder’s full name. |
| **GET**  | `/api/payment/transactions/` | List transaction history (filterable). |
| **GET**  | `/api/user/users/` | **Admin only** – List all users with their account numbers and balances. |

All endpoints are protected by JWT authentication (`IsAuthenticated`). The admin‑only view checks `user_type == 'admin'`.

---

## 📄 .gitignore
A ready‑made ``.gitignore`` is included in the repo (see the file created alongside this README).

---

## 🛠️ Production Tips
- Set ``ENVIRONMENT=PRODUCTION`` in ``.env``.
- Provide real values for ``ALLOWED_HOSTS`` and ``CORS_ALLOWED_ORIGINS``.
- Switch ``EMAIL_BACKEND`` to an SMTP backend and fill the related ``EMAIL_*`` variables.
- Use a proper database (PostgreSQL, MySQL, etc.) and set ``DATABASE_URL`` accordingly.
- Run the app behind a WSGI server such as **Gunicorn** or **Uvicorn**, e.g.:
  ```bash
  gunicorn speedpay_project.wsgi:application --bind 0.0.0.0:8000
  ```

---

## 🎉 Enjoy!
Feel free to open issues or pull requests. Happy coding!
