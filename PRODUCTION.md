# ITAM Linux Production Runbook

This runbook is for Linux servers using Docker Compose.

## 1. First Deployment

Install Docker Engine and Docker Compose Plugin, then clone or upload this project to the server.

```bash
cd itam-system
cp .env.production.example .env.production
chmod +x scripts/prod-init-db.sh
```

Edit `.env.production` before startup. These values must be changed:

- `MYSQL_ROOT_PASSWORD`
- `MYSQL_PASSWORD`
- `DB_PASSWORD`
- `JWT_SECRET`
- `INITIAL_ADMIN_PASSWORD`
- `INITIAL_AUDITOR_PASSWORD`
- `INIT_DATABASE_TOKEN`
- `CORS_ORIGINS`
- `VITE_MOBILE_PUBLIC_URL`

Production startup refuses weak default admin/auditor passwords.

Build and initialize the system:

```bash
docker compose -p itam-prod -f docker-compose.prod.yml --env-file .env.production build
./scripts/prod-init-db.sh
docker compose -p itam-prod -f docker-compose.prod.yml --env-file .env.production up -d
```

Check service status:

```bash
docker compose -p itam-prod -f docker-compose.prod.yml --env-file .env.production ps
docker compose -p itam-prod -f docker-compose.prod.yml --env-file .env.production logs -f backend
```

Do not run `docker compose down -v` in production unless you intentionally want to delete all Docker volume data.

## 2. Production Runtime

Production uses:

- Nginx static frontend, not Vite dev server
- Gunicorn + Uvicorn workers, no reload
- MySQL without public port exposure
- Backend behind frontend `/backend`
- Persistent Docker volumes for MySQL, uploads, reports, backups, and `/app/runtime`

Runtime database configuration is stored under `/app/runtime` in the backend container and is persisted by `backend_runtime_prod`.

## 3. Database Configuration

Keep `MYSQL_*` and `DB_*` consistent in `.env.production`:

- `MYSQL_DATABASE` / `DB_NAME`
- `MYSQL_USER` / `DB_USER`
- `MYSQL_PASSWORD` / `DB_PASSWORD`
- `DB_HOST=mysql` and `DB_PORT=3306` when using the bundled Compose database

Connection pool defaults:

- `DB_POOL_SIZE=10`
- `DB_MAX_OVERFLOW=20`
- `DB_POOL_RECYCLE=1800`
- `DB_POOL_TIMEOUT=30`
- `DB_CONNECT_TIMEOUT=10`

If the database is changed from the admin backend page, restart the backend, run migration, then run initialization:

```bash
docker compose -p itam-prod -f docker-compose.prod.yml --env-file .env.production restart backend
docker compose -p itam-prod -f docker-compose.prod.yml --env-file .env.production exec -T backend alembic upgrade head
./scripts/prod-init-db.sh
```

## 4. Migration

Run Alembic for every release:

```bash
docker compose -p itam-prod -f docker-compose.prod.yml --env-file .env.production exec -T backend alembic upgrade head
```

Check current revision:

```bash
docker compose -p itam-prod -f docker-compose.prod.yml --env-file .env.production exec -T backend alembic current
```

The first migration creates the base tables. Later migrations adjust schema incrementally.

## 5. System Initialization

The initialization API is:

```text
POST /ops/init-database
Header: X-Init-Token: <INIT_DATABASE_TOKEN>
Body: {"force": true}
```

It creates missing tables and seeds:

- Initial administrator and auditor
- Roles and base permissions
- Audit rules
- Notification settings
- Repair fault types
- Product catalog seed data

On Linux, use:

```bash
./scripts/prod-init-db.sh
```

## 6. Backup

The production Compose file includes an automatic backup container.

Defaults:

- Full database backup every 24 hours
- Upload attachment archive every 24 hours
- Keep backups for 14 days

Manual Linux backup:

```bash
BACKUP_DIR="backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
docker compose -p itam-prod -f docker-compose.prod.yml --env-file .env.production exec -T mysql sh -c 'mysqldump -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" --single-transaction --routines --triggers --events "$MYSQL_DATABASE"' > "$BACKUP_DIR/database.sql"
docker compose -p itam-prod -f docker-compose.prod.yml --env-file .env.production exec -T backend tar -czf - /app/uploads > "$BACKUP_DIR/uploads.tar.gz"
```

## 7. Restore

Restore database:

```bash
docker compose -p itam-prod -f docker-compose.prod.yml --env-file .env.production exec -T mysql sh -c 'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"' < backups/YYYYMMDD-HHMMSS/database.sql
```

Restore attachments:

```bash
docker compose -p itam-prod -f docker-compose.prod.yml --env-file .env.production exec -T backend tar -xzf - -C / < backups/YYYYMMDD-HHMMSS/uploads.tar.gz
```

After restore:

```bash
docker compose -p itam-prod -f docker-compose.prod.yml --env-file .env.production restart backend frontend
docker compose -p itam-prod -f docker-compose.prod.yml --env-file .env.production exec -T backend alembic upgrade head
```

Run a restore drill before first production use and after any major schema change.

## 8. Security Checklist

- Change built-in admin and auditor passwords.
- Keep `INIT_DATABASE_TOKEN` secret and rotate it after initial deployment if needed.
- Use HTTPS in front of Nginx when exposed outside LAN.
- Set `CORS_ORIGINS` to the real domain, not `*`.
- Keep `JWT_SECRET` long and random.
- Do not expose MySQL publicly.
- Limit attachment file types and size with `ALLOWED_UPLOAD_EXTENSIONS` and `MAX_UPLOAD_SIZE_MB`.
- Review RBAC before inviting real users.

## 9. Role Intent

- `admin`: full system administration.
- `asset_manager`: asset operation, purchase, repair, supplier, file management.
- `dept_manager`: department-scoped asset operation and repair.
- `auditor`: read assets, read files, run/export audits.
- `user`: read own scoped assets and catalog only.

## 10. Report Exports

Before first production use, download these reports once with an admin account and a department manager account to confirm data-scope isolation:

- Department asset list
- Person holding list
- Overdue borrowing list
- Warranty expiring list
- Scrap and disposal ledger
- Audit report PDF
- Audit report Excel

## 11. Mobile Stocktake Scan Acceptance

Field stocktake needs a separate real-device pass:

- WeChat embedded browser opens `/mobile` successfully.
- Feishu embedded browser opens `/mobile` successfully.
- Chrome/Safari mobile browser opens `/mobile` successfully.
- HTTPS is enabled and camera permission can be granted.
- Browser scan can parse `ITAM-ASSET:<asset_id>|...` QR content.
- Feishu JS SDK scan works when `VITE_FEISHU_SDK_URL` is configured.
- Failed Feishu SDK scan falls back to browser scan.
- Scanning an asset inside the current stocktake task marks it checked.
- Scanning an asset outside the current task shows a clear error.
- Location mismatch or user mismatch can be reported and reviewed.
