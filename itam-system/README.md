# ITAM FastAPI Backend

This directory contains the FastAPI backend for the ITAM asset management system.

## Stack

- Python 3.11
- FastAPI
- SQLAlchemy
- MySQL / SQLite
- Pydantic
- Jinja2
- Alembic
- Uvicorn

## Run With Docker Compose

From the repository root:

```powershell
docker compose -p itam up --build -d
```

Backend URL:

```text
http://127.0.0.1:8000
```

API docs:

```text
http://127.0.0.1:8000/docs
```

## Local Run

```powershell
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

When `DATABASE_URL` is not configured, the backend uses local SQLite:

```text
sqlite:///./itam.db
```

For MySQL:

```powershell
$env:DATABASE_URL="mysql+pymysql://itam:itam_pass@127.0.0.1:3306/itam_system?charset=utf8mb4"
```

## Authentication

Public endpoints:

- `GET /`
- `POST /auth/login`
- `GET /auth/sso/{provider_type}/start`
- `GET /auth/callback/{provider_type}`
- `/docs`
- `/openapi.json`

All business endpoints require:

```http
Authorization: Bearer <jwt>
```

Login example:

```json
{
  "username": "admin",
  "password": "admin",
  "provider": "local"
}
```

The login response includes a signed JWT, expiration seconds, and user details. Passwords are stored with PBKDF2 hashes. Repeated failed logins increase the failure counter and can lock the account for the configured duration.

## Security And Identity

- JWT access tokens
- PBKDF2 password hashing
- Failed-login counter and lockout
- LDAP bind login adapter
- OIDC authorization URL generation and callback login foundation
- SAML SSO URL and callback login foundation
- RBAC table with `role`, `resource`, `action`, `allowed`
- Admin role bypasses RBAC checks
- User and auditor roles are seeded with default permissions

## Main API Groups

### Asset

- `GET /asset/list`
- `POST /asset/create`
- `PUT /asset/{asset_id}`
- `POST /asset/{asset_id}/status`
- `POST /asset/import`
- `POST /asset/import/text`

### Purchase

- `GET /purchase/list`
- `POST /purchase/create`
- `POST /purchase/accept?purchase_no=...`
- `POST /purchase/receive?purchase_no=...`

`/purchase/accept` supports multi-item acceptance. Each purchase item can generate multiple accepted assets with serial numbers and asset details.

### Catalog

- `GET /catalog/device-types`
- `POST /catalog/device-types`
- `PUT /catalog/device-types/{id}`
- `GET /catalog/products`
- `POST /catalog/products`
- `PUT /catalog/products/{id}`

### Identity

- `GET /users/list`
- `POST /users/sync`
- `GET /identity/providers`
- `POST /identity/providers`
- `PUT /identity/providers/{id}`
- `POST /identity/providers/{id}/test`
- `GET /rbac/permissions`

### Files

- `POST /files/asset/{asset_id}/upload`
- `GET /files/asset/{asset_id}`
- `GET /files/{file_id}/download`
- `GET /files/asset/{asset_id}/qrcode`

### Reports

- `GET /reports/assets.csv`
- `GET /reports/assets.pdf`

### Audit

- `POST /audit/run`
- `GET /audit/report`

## Alembic

The project includes Alembic scaffolding:

```powershell
alembic revision --autogenerate -m "change description"
alembic upgrade head
```

The current app startup still calls SQLAlchemy `create_all` and a compatibility patch for existing demo databases, so old local data can continue to boot while migrations are introduced.

## Directory Structure

```text
app/
├── api/
├── core/
├── models/
├── reports/
├── rules/
├── schemas/
└── services/
```
