# ITAM 企业 IT 资产管理系统

一套可容器化运行的企业 IT 资产管理系统，覆盖资产台账、产品档案、采购验收、出入库、报废审批、盘点、审计、风险分析、报表、用户目录、RBAC 权限和 LDAP/OIDC/SAML 身份源配置。

## 技术栈

后端：

- Python 3.11
- FastAPI
- SQLAlchemy
- MySQL 8.0
- Pydantic
- Jinja2
- Alembic
- Uvicorn

前端：

- Vue 3
- Vite
- Element Plus
- Vue Router
- Pinia
- Axios
- ECharts
- Nginx

容器：

- Docker Compose
- MySQL 容器
- FastAPI 后端容器
- Nginx 前端容器

## 快速启动

推荐使用容器部署：

```powershell
.\scripts\container-deploy.ps1 -Rebuild
```

或直接使用 Docker Compose：

```powershell
docker compose -p itam up --build -d
```

访问地址：

- 前端：http://127.0.0.1:5173
- 后端 API：http://127.0.0.1:8000
- API 文档：http://127.0.0.1:8000/docs
- MySQL：127.0.0.1:3306

停止服务：

```powershell
docker compose -p itam down
```

重置数据库并重建：

```powershell
.\scripts\container-deploy.ps1 -Rebuild -ResetData
```

## 默认账号

打开前端登录页：

```text
http://127.0.0.1:5173/login
```

默认管理员：

```text
账号：admin
密码：admin
登录方式：本地
```

默认审计员：

```text
账号：auditor
密码：auditor
登录方式：本地
```

## 已实现的安全能力

- 正式 Bearer JWT 登录令牌
- PBKDF2 密码哈希
- 登录失败计数
- 账号自动锁定
- 前端路由守卫
- 后端接口鉴权中间件
- 基于角色、资源、动作的 RBAC 权限表
- 管理员绕过权限表，普通角色按权限表校验
- LDAP 登录适配
- OIDC/SAML 跳转与回调登录基础流程

未登录访问业务 API 会返回 `401`。前端退出登录会清理 token 和用户信息，并跳转回 `/login`。

## 核心功能

资产管理：

- 资产列表、搜索、筛选
- 批量导入资产
- 批量入库、批量出库
- 资产信息编辑
- 资产详情、二维码、附件上传下载
- 生命周期记录
- 报废申请

资产状态：

- 待验收
- 在库
- 在用
- 闲置
- 借出
- 维修
- 已出库
- 待报废
- 已报废

采购管理：

- 创建采购单
- 审批单号、供应商、申请部门等信息
- 一张采购单支持多种设备明细
- 每个明细可关联产品档案
- 验收时逐台填写序列号、资产名称、规格、部门、责任人、位置和仓库
- 验收后自动生成资产并入库

产品与设备类型：

- 手动新增/编辑设备类型
- 维护产品档案
- 产品名称、品牌、型号、规格、默认仓库、单价可复用
- 采购和资产录入时可关联产品档案，减少重复填写

审计与风险：

- 规则引擎
- 审计引擎
- 风险评分
- HTML 审计报告生成
- 资产闲置、高价值资产未绑定部门、用户资产超配等规则

报表与文件：

- 资产 CSV 导出
- 资产 PDF 导出
- 资产附件上传和下载
- 资产二维码生成

## 常用 API

Auth：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/auth/login` | 本地/LDAP 登录并返回 JWT |
| GET | `/auth/sso/{provider_type}/start` | 获取 OIDC/SAML 跳转地址 |
| GET | `/auth/callback/{provider_type}` | OIDC/SAML 回调登录 |

Asset：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/asset/list` | 资产列表 |
| POST | `/asset/create` | 创建资产 |
| PUT | `/asset/{asset_id}` | 更新资产信息 |
| POST | `/asset/{asset_id}/status` | 修改资产状态 |
| POST | `/asset/import` | JSON 批量导入资产 |
| POST | `/asset/import/text` | CSV/表格文本导入资产 |

Purchase：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/purchase/list` | 采购单列表 |
| POST | `/purchase/create` | 创建采购单 |
| POST | `/purchase/accept?purchase_no=...` | 按验收明细生成资产 |
| POST | `/purchase/receive?purchase_no=...` | 兼容旧版一键入库 |

Identity & RBAC：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/users/list` | 用户目录 |
| POST | `/users/sync` | 同步用户 |
| GET | `/identity/providers` | 身份源列表 |
| POST | `/identity/providers` | 新增身份源 |
| PUT | `/identity/providers/{id}` | 修改身份源 |
| POST | `/identity/providers/{id}/test` | 测试身份源配置 |
| GET | `/rbac/permissions` | RBAC 权限列表 |

Files & Reports：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/files/asset/{asset_id}/upload` | 上传资产附件 |
| GET | `/files/asset/{asset_id}` | 附件列表 |
| GET | `/files/{file_id}/download` | 下载附件 |
| GET | `/files/asset/{asset_id}/qrcode` | 资产二维码 |
| GET | `/reports/assets.csv` | 导出资产 CSV |
| GET | `/reports/assets.pdf` | 导出资产 PDF |

## 数据库迁移

项目已加入 Alembic：

```powershell
cd itam-system
alembic revision --autogenerate -m "change description"
alembic upgrade head
```

当前容器启动时仍会执行 SQLAlchemy `create_all`，并包含旧库兼容补丁，方便从已有演示数据平滑升级。

## 开发模式

需要前后端热更新时：

```powershell
.\scripts\container-dev.ps1 -Rebuild
```

等价命令：

```powershell
docker compose -p itam -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

部署模式使用 Nginx 静态前端；开发模式会挂载本地源码，适合持续改代码。

## 项目结构

```text
.
├── docker-compose.yml
├── docker-compose.dev.yml
├── DOCKER.md
├── README.md
├── scripts/
│   ├── container-deploy.ps1
│   └── container-dev.ps1
├── itam-system/
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── alembic/
│   ├── requirements.txt
│   └── app/
│       ├── api/
│       ├── core/
│       ├── models/
│       ├── schemas/
│       ├── services/
│       ├── rules/
│       └── reports/
└── itam-frontend/
    ├── Dockerfile
    ├── Dockerfile.dev
    ├── nginx.conf
    ├── package.json
    └── src/
        ├── api/
        ├── components/
        ├── layout/
        ├── router/
        ├── store/
        └── views/
```

## 环境变量

后端主要环境变量：

```text
DATABASE_URL=mysql+pymysql://itam:itam_pass@mysql:3306/itam_system?charset=utf8mb4
JWT_SECRET=change-this-secret
JWT_EXPIRE_MINUTES=480
LOGIN_LOCK_THRESHOLD=5
LOGIN_LOCK_MINUTES=15
UPLOAD_DIR=/app/uploads
AUDIT_REPORT_PATH=/app/audit_report.html
MAX_ASSETS_PER_USER=5
HIGH_VALUE_THRESHOLD=50000
IDLE_DAYS_THRESHOLD=90
```

前端构建变量：

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```
