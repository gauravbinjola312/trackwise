# TrackWise Backend — Django REST API

Production-ready Django backend for the TrackWise personal finance app.
Handles up to **500 users** on free-tier infrastructure.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Django 4.2 + Django REST Framework |
| Auth | JWT (SimpleJWT) — access + refresh tokens |
| Database | PostgreSQL |
| Cache | Redis |
| Payments | Razorpay subscriptions |
| Tasks | Celery (background email, etc.) |
| Hosting | Railway / Render / Heroku / VPS |

---

## Project Structure

```
trackwise-backend/
├── manage.py
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── Procfile                          ← Heroku / Railway deploy
├── trackwise_backend/
│   ├── settings/
│   │   ├── base.py                   ← Shared settings
│   │   ├── development.py            ← Local dev overrides
│   │   └── production.py             ← Production overrides
│   ├── apps/
│   │   ├── accounts/                 ← User auth (register, login, JWT)
│   │   │   ├── models.py             ← User, Profile, EmailVerificationToken
│   │   │   ├── serializers.py        ← Request/response shapes
│   │   │   ├── views.py              ← 10 auth endpoints
│   │   │   ├── urls.py
│   │   │   └── admin.py
│   │   ├── expenses/                 ← Expense CRUD
│   │   ├── learning/                 ← Learning session CRUD
│   │   ├── goals/                    ← Goal CRUD + progress tracking
│   │   ├── savings/                  ← Investment CRUD
│   │   ├── subscriptions/            ← Razorpay billing + webhook
│   │   └── dashboard/               ← Rule engine + combined stats
│   └── utils/
│       ├── exceptions.py             ← Consistent error format
│       ├── middleware.py             ← Request logging
│       ├── pagination.py             ← Standard pagination
│       ├── mixins.py                 ← SuccessResponseMixin, UserOwnedQuerysetMixin
│       ├── permissions.py            ← IsSubscriptionActive, IsOwner
│       └── validators.py             ← Shared field validators
├── scripts/
│   ├── setup.sh                      ← One-command local setup
│   └── seed_data.py                  ← Populate test data (500 users)
└── docs/
    └── API_REFERENCE.md              ← Complete API docs
```

---

## Quick Start (Local)

### Option A — Automated (recommended)
```bash
git clone <repo>
cd trackwise-backend
bash scripts/setup.sh
```

### Option B — Manual
```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate          # macOS/Linux
venv\Scripts\activate             # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — fill in DB credentials, secret key

# 4. Run migrations
export DJANGO_SETTINGS_MODULE=trackwise_backend.settings.development
python manage.py migrate

# 5. Create superuser (for /admin panel)
python manage.py createsuperuser

# 6. Start server
python manage.py runserver
```

**API running at:** http://localhost:8000/api/v1/
**Admin panel:**    http://localhost:8000/admin/
**Health check:**   http://localhost:8000/health/

---

## Option C — Docker (zero setup)

```bash
cp .env.example .env
docker-compose up -d
docker-compose exec api python manage.py migrate
docker-compose exec api python manage.py createsuperuser
```

API at http://localhost:8000

---

## Database Setup (PostgreSQL)

```bash
# Install PostgreSQL, then:
psql -U postgres
CREATE USER trackwise WITH PASSWORD 'password';
CREATE DATABASE trackwise_db OWNER trackwise;
GRANT ALL PRIVILEGES ON DATABASE trackwise_db TO trackwise;
\q
```

Or use Supabase (free, 500MB):
1. supabase.com → New project → copy connection string
2. Set `DATABASE_URL` in .env

---

## Seed Test Data

```bash
# Seed 50 test users (default)
python scripts/seed_data.py

# Seed 500 users (stress test)
python scripts/seed_data.py 500

# Login: user1@trackwise.test / Password123!
```

---

## All API Endpoints

### Auth (no token required)
```
POST   /api/v1/auth/register/
POST   /api/v1/auth/login/
POST   /api/v1/auth/logout/
POST   /api/v1/auth/token/refresh/
POST   /api/v1/auth/forgot-password/
POST   /api/v1/auth/reset-password/
POST   /api/v1/auth/verify-email/
```

### Auth (token required)
```
GET    /api/v1/auth/me/
PATCH  /api/v1/auth/profile/
POST   /api/v1/auth/change-password/
DELETE /api/v1/auth/account/
```

### Expenses
```
GET    /api/v1/expenses/                    ← list + filter
POST   /api/v1/expenses/                    ← create
GET    /api/v1/expenses/{id}/               ← detail
PUT    /api/v1/expenses/{id}/               ← full update
PATCH  /api/v1/expenses/{id}/               ← partial update
DELETE /api/v1/expenses/{id}/               ← delete
POST   /api/v1/expenses/bulk-create/        ← create many
DELETE /api/v1/expenses/bulk-delete/        ← delete many
GET    /api/v1/expenses/summary/            ← 30-day stats
```

### Learning
```
GET/POST  /api/v1/learning/
GET/PATCH/DELETE  /api/v1/learning/{id}/
GET       /api/v1/learning/summary/
GET       /api/v1/learning/heatmap/         ← 14-day activity grid
```

### Goals
```
GET/POST  /api/v1/goals/
GET/PATCH/DELETE  /api/v1/goals/{id}/
PATCH     /api/v1/goals/{id}/progress/      ← quick progress update
GET       /api/v1/goals/summary/
```

### Savings
```
GET/POST  /api/v1/savings/
GET/PATCH/DELETE  /api/v1/savings/{id}/
GET       /api/v1/savings/summary/
```

### Dashboard (most important)
```
GET       /api/v1/dashboard/                ← all data in one call
GET       /api/v1/dashboard/alerts/         ← rule alerts only
GET       /api/v1/dashboard/export/         ← full data export
```

### Subscriptions
```
GET/POST  /api/v1/subscriptions/
POST      /api/v1/subscriptions/cancel/
GET       /api/v1/subscriptions/history/
POST      /api/v1/subscriptions/webhook/    ← Razorpay (no auth)
```

---

## Authentication Flow

```
1. User POSTs to /auth/register/ or /auth/login/
2. Server returns { access: "...", refresh: "..." }
3. Client stores BOTH tokens (AsyncStorage on mobile)
4. Every API request includes: Authorization: Bearer <access>
5. When access token expires (60 min):
   → POST /auth/token/refresh/ with refresh token → get new access
6. When refresh token expires (30 days) → user must login again
```

---

## Razorpay Integration

```
1. Client: POST /api/v1/subscriptions/ { plan: "yearly" }
2. Server: Creates Razorpay subscription → returns subscription_id
3. Client: Opens Razorpay checkout with subscription_id
4. User: Pays in Razorpay UI
5. Razorpay: POSTs to /api/v1/subscriptions/webhook/
6. Server: Verifies signature → updates subscription to "active"
7. User: Can now access premium features
```

**Webhook URL to set in Razorpay Dashboard:**
`https://your-domain.com/api/v1/subscriptions/webhook/`

---

## Deploy to Railway (free tier)

```bash
# Install Railway CLI
npm install -g @railway/cli
railway login

# Create new project
railway init

# Add PostgreSQL
railway add postgresql

# Add Redis
railway add redis

# Set environment variables
railway variables set DJANGO_SETTINGS_MODULE=trackwise_backend.settings.production
railway variables set DJANGO_SECRET_KEY=your-secret-key
# ... all other env vars

# Deploy
railway up
```

Railway free tier: 500 hours/month, 100GB bandwidth — enough for 500 users.

---

## Deploy to Render (free tier)

1. Create account at render.com
2. New → Web Service → connect GitHub repo
3. Build command: `pip install -r requirements.txt && python manage.py migrate`
4. Start command: `gunicorn trackwise_backend.wsgi:application`
5. Add environment variables from .env
6. Add PostgreSQL database (free)

---

## Performance at 500 Users

| Metric | Value |
|--------|-------|
| DB size (500 users × 100 rows each) | ~50MB |
| Supabase free tier limit | 500MB |
| API response time (cached) | <50ms |
| API response time (DB query) | <200ms |
| Concurrent users (Railway/Render) | 100+ |
| Cost | ₹0/month |

At 500 paying users × ₹199 = **₹99,500/month revenue, ₹0 infrastructure**.

---

## Running Tests

```bash
pytest
pytest --cov=trackwise_backend --cov-report=html
# Open htmlcov/index.html
```

---

## Common Commands

```bash
# Create new migration
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Django shell
python manage.py shell

# Collect static files (production)
python manage.py collectstatic --no-input

# Seed test data
python scripts/seed_data.py 50

# Check for issues
python manage.py check --deploy
```
