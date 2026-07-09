# ITAM Production Runbook

## 1. Prepare environment

Copy `.env.production.example` to `.env.production` and change every password/secret before startup.

Required values:

- `MYSQL_ROOT_PASSWORD`
- `MYSQL_PASSWORD`
- `DB_PASSWORD`
- `JWT_SECRET`
- `INITIAL_ADMIN_PASSWORD`
- `INITIAL_AUDITOR_PASSWORD`
- `CORS_ORIGINS`

Production startup refuses weak default admin/auditor passwords.

## 2. Start production

```powershell
.\scripts\prod-up.ps1 -Build
```

Production uses:

- Nginx static frontend, not Vite dev server
- Gunicorn + Uvicorn workers, no reload
- MySQL without public port exposure
- Backend behind frontend `/backend`
- Persistent Docker volumes for MySQL, uploads, reports, backups

## 2.1 Database configuration

Production uses MySQL. Keep `MYSQL_*` and `DB_*` consistent in `.env.production`:

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

MySQL container defaults:

- `MYSQL_MAX_CONNECTIONS=200`
- `MYSQL_INNODB_BUFFER_POOL_SIZE=512M`
- `MYSQL_TIMEZONE=+08:00`

For a small server, keep the defaults first. For a larger concurrent deployment, increase `MYSQL_MAX_CONNECTIONS` together with backend worker count and database pool size.

## 3. Database migration

Production migration is fixed to Alembic:

```powershell
docker compose -p itam-prod -f docker-compose.prod.yml --env-file .env.production exec backend alembic upgrade head
```

The backend image also runs `alembic upgrade head` on container startup.

Do not use `docker compose down -v` in production unless you intentionally want to delete all data.

## 4. Backup

The production compose includes an automatic backup container.

Defaults:

- Full database backup every 24 hours
- Upload attachment archive every 24 hours
- Keep backups for 14 days

Manual backup:

```powershell
.\scripts\prod-backup.ps1
```

## 5. Restore drill

Restore database:

```powershell
.\scripts\prod-restore.ps1 -BackupPath .\backups\YYYYMMDD-HHMMSS
```

Restore database and attachments:

```powershell
.\scripts\prod-restore.ps1 -BackupPath .\backups\YYYYMMDD-HHMMSS -RestoreUploads
```

Run a restore drill before first production use and after any major schema change.

## 6. Security checklist

- Change built-in admin and auditor passwords.
- Use HTTPS in front of Nginx when exposed outside LAN.
- Set `CORS_ORIGINS` to the real domain, not `*`.
- Keep `JWT_SECRET` long and random.
- Do not expose MySQL publicly.
- Limit attachment file types and size with `ALLOWED_UPLOAD_EXTENSIONS` and `MAX_UPLOAD_SIZE_MB`.
- Review RBAC before inviting real users.

## 7. Role intent

- `admin`: full system administration.
- `asset_manager`: asset operation, purchase, repair, supplier, file management.
- `dept_manager`: department-scoped asset operation and repair.
- `auditor`: read assets, read files, run/export audits.
- `user`: read own scoped assets and catalog only.

## 8. Report exports

The report center includes production ledger exports:

- Department asset list
- Person holding list
- Overdue borrowing list
- Warranty expiring list
- Scrap and disposal ledger
- Audit report PDF
- Audit report Excel

Before first production use, download each report once with an admin account and a department manager account to confirm data-scope isolation.

## 9. Mobile stocktake scan acceptance

PC workflows can go live first. Field stocktake needs a separate real-device pass:

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
