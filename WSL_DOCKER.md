# WSL2 + Docker 开发指南

可以使用 WSL2 进行本项目的 Docker 开发，推荐方式是：

- Windows 安装 WSL2 + Ubuntu
- Docker Desktop 开启 WSL Integration
- 在 WSL 的 Linux 文件系统里运行 `docker compose`

## 1. 安装 WSL2

在 Windows PowerShell 管理员模式执行：

```powershell
wsl --install
```

安装完成后重启电脑。默认会安装 Ubuntu。

查看状态：

```powershell
wsl --status
wsl -l -v
```

确保 Ubuntu 是 `VERSION 2`。如果不是：

```powershell
wsl --set-version Ubuntu 2
```

## 2. 安装 Docker Desktop 并启用 WSL

安装 Docker Desktop 后打开：

```text
Settings -> Resources -> WSL Integration
```

开启：

- Enable integration with my default WSL distro
- Ubuntu

然后在 Ubuntu 终端验证：

```bash
docker --version
docker compose version
```

## 3. 推荐项目目录

推荐把项目放在 WSL 文件系统里，而不是直接在 `/mnt/c/...` 下运行。

例如：

```bash
mkdir -p ~/projects
cp -r /mnt/c/Users/Administrator/Documents/资产管理系统 ~/projects/itam
cd ~/projects/itam
```

如果直接在 `/mnt/c` 运行，文件监听和依赖安装会慢一些。

## 4. 启动前后端联调环境

在项目根目录执行：

```bash
docker compose up --build
```

访问：

- 前端：http://127.0.0.1:5173
- 后端：http://127.0.0.1:8000
- API 文档：http://127.0.0.1:8000/docs
- MySQL：127.0.0.1:3306

## 5. 常用命令

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f mysql
docker compose down
```

重置数据库：

```bash
docker compose down -v
docker compose up --build
```

## 6. 联调说明

前端通过 Vite 代理访问后端：

```text
/backend -> http://backend:8000
```

浏览器访问前端时，顶部栏会请求：

```text
/backend/
```

如果显示“后端已连接”，说明前端容器、Vite proxy、FastAPI 后端已经连通。
