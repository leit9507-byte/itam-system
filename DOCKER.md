# ITAM Container Guide

This project supports two container modes.

## First Deployment

Use the first-deploy script on a new server or a fresh workstation. It checks Docker Compose, creates `.env` from `.env.example` when available, rebuilds images, starts containers, and prints the service URLs.

```powershell
.\scripts\first-deploy.ps1
```

Linux/macOS:

```bash
bash scripts/first-deploy.sh
```

To rebuild from an empty database during the first rollout:

```powershell
.\scripts\first-deploy.ps1 -ResetData
```

Mobile entry variables can be set in `.env` before building:

```text
VITE_MOBILE_PUBLIC_URL=https://it.example.com/mobile
VITE_FEISHU_SDK_URL=https://lf1-cdn-tos.bytegoofy.com/goofy/lark/op/h5-js-sdk-1.5.30.js
VITE_FEISHU_SDK_AUTO_LOAD=true
```

After changing these frontend build variables, rebuild the frontend image with `.\scripts\container-deploy.ps1 -Rebuild`.

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
