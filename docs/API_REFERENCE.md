# TrackWise API Reference

Base URL: `http://localhost:8000/api/v1/`

All authenticated endpoints require:
```
Authorization: Bearer <access_token>
```

All responses follow this shape:
```json
{ "success": true, "data": { ... } }
{ "success": false, "error": { "code": "...", "message": "..." } }
```

---

## Authentication Flow

```
SIGNUP → returns tokens → store in device → use for every request
TOKEN EXPIRES (60 min) → call /auth/token/refresh/ with refresh token → get new access token
REFRESH TOKEN EXPIRES (30 days) → user must login again
```

---

## Auth Endpoints

### POST /api/v1/auth/register/
Create a new account. Returns JWT tokens immediately.

**Request:**
```json
{
  "full_name": "Rahul Sharma",
  "email": "rahul@example.com",
  "password": "Secret123!",
  "password_confirm": "Secret123!"
}
```

**Response 201:**
```json
{
  "success": true,
  "message": "Account created successfully. Please verify your email.",
  "data": {
    "access": "eyJ...",
    "refresh": "eyJ...",
    "user": {
      "id": "uuid",
      "email": "rahul@example.com",
      "full_name": "Rahul Sharma",
      "is_email_verified": false,
      "created_at": "2024-01-15T10:30:00Z",
      "profile": {
        "monthly_income": "0.00",
        "currency": "INR",
        "avatar_url": "",
        "timezone": "Asia/Kolkata",
        "notifications_enabled": true
      }
    }
  }
}
```

---

### POST /api/v1/auth/login/
**Request:** `{ "email": "...", "password": "..." }`
**Response:** Same as register, with tokens + user object.

---

### POST /api/v1/auth/logout/
**Request:** `{ "refresh": "eyJ..." }`
Blacklists the refresh token. Both tokens become invalid.

---

### POST /api/v1/auth/token/refresh/
Get a new access token before it expires.
**Request:** `{ "refresh": "eyJ..." }`
**Response:** `{ "access": "eyJ...", "refresh": "eyJ..." }`

---

### GET /api/v1/auth/me/
Get current user info. Requires Bearer token.

---

### PATCH /api/v1/auth/profile/
Update profile. All fields optional.
```json
{
  "full_name": "Rahul S",
  "monthly_income": "80000",
  "currency": "INR",
  "timezone": "Asia/Kolkata",
  "notifications_enabled": true
}
```

---

### POST /api/v1/auth/change-password/
```json
{ "current_password": "old", "new_password": "New123!", "new_password_confirm": "New123!" }
```

---

### POST /api/v1/auth/forgot-password/
`{ "email": "rahul@example.com" }` → Sends reset link. Always returns 200.

### POST /api/v1/auth/reset-password/
`{ "token": "uuid", "new_password": "New123!", "new_password_confirm": "New123!" }`

### POST /api/v1/auth/verify-email/
`{ "token": "uuid" }` — from the email link.

### DELETE /api/v1/auth/account/
`{ "password": "current_password" }` — Soft-deletes account.

---

## Expenses

### GET /api/v1/expenses/
List all expenses with pagination + filters.

**Query params:**
| Param      | Example              | Description              |
|------------|----------------------|--------------------------|
| page       | `?page=2`            | Page number              |
| page_size  | `?page_size=25`      | Items per page (max 200) |
| category   | `?category=Food`     | Filter by category       |
| payment    | `?payment=UPI`       | Filter by payment mode   |
| date_from  | `?date_from=2024-01-01` | From date (inclusive)|
| date_to    | `?date_to=2024-01-31`   | To date (inclusive)  |
| min_amount | `?min_amount=500`    | Minimum amount           |
| max_amount | `?max_amount=5000`   | Maximum amount           |
| search     | `?search=zomato`     | Search description/notes |
| ordering   | `?ordering=-amount`  | Sort (prefix `-` = desc) |

**Response:**
```json
{
  "success": true,
  "pagination": { "count": 120, "pages": 5, "current": 1, "next": "...", "previous": null },
  "results": [
    {
      "id": "uuid",
      "date": "2024-01-15",
      "description": "Zomato Order",
      "category": "Food",
      "amount": "320.00",
      "payment": "UPI",
      "row_flag": "yellow",
      "created_at": "2024-01-15T18:30:00Z"
    }
  ]
}
```

**Row flag values:** `red` (>₹1000) | `yellow` (Food>₹400 / Entertainment>₹200) | `green`

---

### POST /api/v1/expenses/
```json
{
  "date": "2024-01-15",
  "description": "Zomato Order",
  "category": "Food",
  "amount": "320.00",
  "payment": "UPI",
  "notes": "Optional"
}
```

### PATCH /api/v1/expenses/{id}/
Partial update. Send only fields to change.

### DELETE /api/v1/expenses/{id}/
Returns 204 No Content.

### POST /api/v1/expenses/bulk-create/
```json
[
  { "date": "2024-01-15", "description": "Zomato", "category": "Food", "amount": 320, "payment": "UPI", "notes": "" },
  { "date": "2024-01-15", "description": "Uber", "category": "Transport", "amount": 180, "payment": "UPI", "notes": "" }
]
```

### DELETE /api/v1/expenses/bulk-delete/
`{ "ids": ["uuid1", "uuid2"] }`

### GET /api/v1/expenses/summary/?days=30
Returns totals + category breakdown + flag counts.

---

## Learning

### GET /api/v1/learning/
Similar to expenses. Filters: `status`, `source`, `date_from`, `date_to`

### POST /api/v1/learning/
```json
{
  "date": "2024-01-15",
  "topic": "React Native",
  "source": "Online Course",
  "hours": "2.0",
  "status": "In Progress",
  "notes": "Udemy - Complete Guide"
}
```

### GET /api/v1/learning/summary/?days=30
```json
{
  "period_days": 30,
  "total_hours": 45.5,
  "period_hours": 18.5,
  "week_hours": 6.5,
  "completed": 3,
  "last_date": "2024-01-15",
  "days_since_last": 0,
  "by_source": [{"source": "Online Course", "hours": 12.5, "count": 5}]
}
```

### GET /api/v1/learning/heatmap/?days=14
```json
{
  "days": 14,
  "cells": [
    { "date": "2024-01-02", "hours": 0, "level": 0 },
    { "date": "2024-01-03", "hours": 1.5, "level": 1 },
    { "date": "2024-01-04", "hours": 2.5, "level": 2 }
  ]
}
```
Level: `0` = none, `1` = any hours, `2` = 2+ hours

---

## Goals

### GET /api/v1/goals/
### POST /api/v1/goals/
```json
{
  "name": "Bike Fund",
  "category": "Finance",
  "target": "100000",
  "current": "72000",
  "deadline": "2024-03-31",
  "notes": "Saving from monthly salary"
}
```

**Response includes computed fields:**
```json
{
  "id": "uuid",
  "name": "Bike Fund",
  "pct_complete": 72.0,
  "days_left": 65,
  "is_overdue": false,
  "daily_required": 424.24,
  "status": "on_track"
}
```

**Status values:** `on_track` | `behind` | `at_risk` | `almost_done` | `overdue`

### PATCH /api/v1/goals/{id}/progress/
Quick progress update: `{ "current": "75000" }`

### GET /api/v1/goals/summary/
Overview of all goals with status distribution.

---

## Savings

### GET /api/v1/savings/
### POST /api/v1/savings/
```json
{
  "date": "2024-01-15",
  "name": "Nifty 50 SIP",
  "type": "SIP",
  "amount": "5000",
  "monthly_income": "80000",
  "platform": "Zerodha",
  "notes": ""
}
```

### GET /api/v1/savings/summary/?days=30
```json
{
  "period_total": 12500,
  "all_time_total": 125000,
  "monthly_income": 80000,
  "savings_rate": 15.6,
  "unique_types": 4,
  "by_type": [
    { "type": "SIP", "amount": 8000, "count": 2, "percentage": 64.0 }
  ]
}
```

---

## Dashboard

### GET /api/v1/dashboard/?days=30
**One API call returns everything** the mobile app needs:
- 6 KPI values
- Expense breakdown for donut chart
- You vs Recommended data for bar chart
- Top 4 goals at a glance
- All rule-engine alerts (sorted red first)
- Subscription status

```json
{
  "period_days": 30,
  "kpis": {
    "active_alerts": 3,
    "total_spent": 45230,
    "food_pct": 18.6,
    "learning_hours": 12.4,
    "saved_amount": 12500,
    "goals_average": 68
  },
  "charts": {
    "expense_breakdown": [
      { "category": "Food", "amount": 8420, "pct": 18.6 }
    ],
    "vs_recommended": [
      { "label": "Food", "your_pct": 18.6, "limit_pct": 45 }
    ]
  },
  "goals_glance": [
    { "id": "uuid", "name": "Bike Fund", "pct_complete": 72, "days_left": 65, "status": "on_track" }
  ],
  "alerts": [
    { "scope": "expense", "sev": "red", "icon": "🔴", "tag": "OVERSPEND",
      "title": "Food is 45% of spending", "desc": "Limit 45%. Cut ₹340 to fix." }
  ],
  "subscription": {
    "status": "trial",
    "is_active": true,
    "trial_days_left": 14,
    "plan": "monthly"
  }
}
```

### GET /api/v1/dashboard/alerts/?days=30
Alerts only (lighter payload).

### GET /api/v1/dashboard/export/
Full data export as JSON.

---

## Subscriptions

### GET /api/v1/subscriptions/
Current subscription status.

### POST /api/v1/subscriptions/
Start payment flow.
**Request:** `{ "plan": "yearly" }` or `{ "plan": "monthly" }`
**Response:**
```json
{
  "subscription_id": "sub_xxxxx",
  "key_id": "rzp_live_xxxx",
  "plan": "yearly",
  "amount": 1999
}
```
Use `subscription_id` with Razorpay checkout SDK.

### POST /api/v1/subscriptions/cancel/
Cancel active subscription at end of billing period.

### GET /api/v1/subscriptions/history/
Last 50 payment events.

### POST /api/v1/subscriptions/webhook/
**No auth.** Razorpay posts here automatically.
Set this URL in your Razorpay Dashboard → Settings → Webhooks.

---

## Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| VALIDATION_ERROR | 400 | Invalid input data |
| AUTHENTICATION_REQUIRED | 401 | Missing or invalid token |
| PERMISSION_DENIED | 403 | Insufficient permissions |
| NOT_FOUND | 404 | Resource does not exist |
| SUBSCRIPTION_REQUIRED | 402 | Premium feature, needs active sub |
| RATE_LIMIT_EXCEEDED | 429 | Too many requests |
| USER_LIMIT_REACHED | 503 | Platform at 500 user capacity |
| INTERNAL_SERVER_ERROR | 500 | Server-side bug (check Sentry) |

---

## Rate Limits

| User type | Limit |
|-----------|-------|
| Anonymous | 100 requests/hour |
| Authenticated | 2,000 requests/hour |

---

## Pagination

Default page size: 50. Maximum: 200.
```
GET /api/v1/expenses/?page=2&page_size=25
```
