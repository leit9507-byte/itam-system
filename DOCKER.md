# ITAM Container Guide

This project supports two container modes.

## Deployment Mode

Fast page load. Frontend is built once and served by Nginx. Backend runs without reload.

```powershell
.\scripts\container-deploy.ps1 -Rebuild
```

Equivalent command:

```powershell
docker compose -p itam up --build -d
```

URLs:

- Frontend: http://127.0.0.1:5173
- Backend API: http://127.0.0.1:8000
- API Docs: http://127.0.0.1:8000/docs
- MySQL: 127.0.0.1:3306

Stop:

```powershell
docker compose -p itam down
```

Reset database:

```powershell
.\scripts\container-deploy.ps1 -Rebuild -ResetData
```

## Development Mode

Hot reload for frontend and backend. This is slower on Windows bind mounts, but useful while editing code.

```powershell
.\scripts\container-dev.ps1 -Rebuild
```

Equivalent command:

```powershell
docker compose -p itam -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

## Why The Frontend Was Slow

The previous default used Vite dev server inside Docker with a Windows bind mount and polling file watching. That is convenient for editing, but it can make first page load and dependency scanning feel slow.

The new default uses:

- Nginx static frontend container
- No frontend bind mount in deployment mode
- Backend without `--reload`
- Separate `docker-compose.dev.yml` for hot reload only when needed
