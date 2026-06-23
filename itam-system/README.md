# ITAM FastAPI Backend

This directory contains the FastAPI backend for the ITAM asset management system.

## Stack

- Python 3.11
- FastAPI
- SQLAlchemy
- MySQL / SQLite
- Pydantic
- Jinja2
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
- `/docs`
- `/openapi.json`

Other endpoints require:

```http
Authorization: Bearer mock-token-...
```

Login example:

```json
{
  "username": "admin",
  "password": "admin",
  "provider": "local"
}
```

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

### Audit

- `POST /audit/run`
- `GET /audit/report`

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

## Notes

The current authentication and LDAP/OIDC/SAML integrations are working foundations for development and demos. Before production use, replace the mock token logic with real JWT/session validation and connect the identity provider adapters to real enterprise systems.
