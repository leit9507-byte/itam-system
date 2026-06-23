# ITAM 企业 IT 资产管理系统

一套可容器化运行的企业 IT 资产管理系统，覆盖资产台账、采购验收、出入库、报废审批、盘点、审计、风险分析、报表、用户目录和基础 SSO/LDAP 集成。

## 技术栈

### 后端

- Python 3.11
- FastAPI
- SQLAlchemy
- MySQL 8.0
- Pydantic
- Jinja2
- Uvicorn

### 前端

- Vue 3
- Vite
- Element Plus
- Vue Router
- Pinia
- Axios
- ECharts
- Nginx 静态部署

### 容器

- Docker Compose
- MySQL 容器
- FastAPI 后端容器
- Nginx 前端容器

## 快速启动

推荐使用容器部署模式：

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

## 默认登录

打开前端后进入登录页：

```text
http://127.0.0.1:5173/login
```

默认账号：

```text
账号：admin
密码：admin
登录方式：本地
```

当前系统已实现基础鉴权：

- 未登录访问业务页面会跳转到 `/login`
- 未携带 Bearer Token 调用业务 API 会返回 `401`
- 登录后前端会保存 token，并自动携带 `Authorization` 请求头
- 登出会清理 token 和用户信息

## 核心功能

### 资产管理

- 资产列表、搜索、筛选
- 批量导入资产
- 批量入库、批量出库
- 资产信息编辑
- 报废申请
- 生命周期记录

资产状态包括：

- 待验收
- 在库
- 在用
- 闲置
- 借出
- 维修
- 已出库
- 待报废
- 已报废

### 采购管理

- 创建采购单
- 一张采购单支持多种设备明细
- 每个明细可选择产品档案
- 验收时按采购明细逐台填写：
  - 序列号
  - 资产名称
  - 规格
  - 部门
  - 使用人
  - 位置/仓库
- 验收后自动生成资产并入库

### 产品与设备类型

- 手动新增/编辑设备类型
- 维护产品档案
- 产品名称、品牌、型号、规格、默认仓库、单价可复用
- 采购和资产录入时可关联产品档案，避免重复填写

### 出入库

- 单个资产出库
- 批量出库
- 批量入库
- 出入库记录用于资产流转追踪

### 报废审批

- 从资产列表发起报废申请
- 支持批量申请报废
- 报废审批通过后资产进入已报废状态

### 盘点

- 盘点任务页面
- 盘点记录
- 差异统计

### 审计与风险

- 规则引擎
- 审计引擎
- 风险评分
- HTML 审计报告生成

已实现规则示例：

- 用户资产数量超限
- 资产闲置超过阈值
- 高价值资产未绑定部门
- 单人资产总价值超阈值

### 用户、权限与身份源

- 用户目录
- 角色：`admin`、`auditor`、`user`
- 基础权限开关 UI
- LDAP / AD 配置
- OIDC 配置
- SAML 配置
- 飞书、企业微信身份源配置占位
- 用户同步 mock 适配层
- 登录测试

> 当前 LDAP / OIDC / SAML 是可运行的基础适配层和配置模型，真实企业认证流程可在现有接口上继续接入。

## 常用 API

### Auth

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/auth/login` | 登录并返回 token |
| GET | `/auth/sso/{provider_type}/start` | 模拟 SSO 跳转 |

### Asset

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/asset/list` | 资产列表 |
| POST | `/asset/create` | 创建资产 |
| PUT | `/asset/{asset_id}` | 更新资产信息 |
| POST | `/asset/{asset_id}/status` | 修改资产状态 |
| POST | `/asset/import` | JSON 批量导入资产 |
| POST | `/asset/import/text` | CSV/表格文本导入资产 |

### Purchase

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/purchase/list` | 采购单列表 |
| POST | `/purchase/create` | 创建采购单 |
| POST | `/purchase/accept?purchase_no=...` | 按验收明细生成资产 |
| POST | `/purchase/receive?purchase_no=...` | 兼容旧版一键入库 |

### Catalog

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/catalog/device-types` | 设备类型列表 |
| POST | `/catalog/device-types` | 新增设备类型 |
| PUT | `/catalog/device-types/{id}` | 修改设备类型 |
| GET | `/catalog/products` | 产品档案列表 |
| POST | `/catalog/products` | 新增产品档案 |
| PUT | `/catalog/products/{id}` | 修改产品档案 |

### User & Identity

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/users/list` | 用户目录 |
| POST | `/users/sync` | 同步用户 |
| GET | `/identity/providers` | 身份源列表 |
| POST | `/identity/providers` | 新增身份源 |
| PUT | `/identity/providers/{id}` | 修改身份源 |
| POST | `/identity/providers/{id}/test` | 测试身份源配置 |

### Audit

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/audit/run` | 执行审计 |
| GET | `/audit/report` | 获取 HTML 审计报告 |

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

## 开发模式

开发时如果需要前后端热更新：

```powershell
.\scripts\container-dev.ps1 -Rebuild
```

等价命令：

```powershell
docker compose -p itam -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

开发模式会挂载本地源码，适合改代码；部署模式使用 Nginx 静态前端，访问更快。

## 环境变量

后端主要环境变量：

```text
DATABASE_URL=mysql+pymysql://itam:itam_pass@mysql:3306/itam_system?charset=utf8mb4
AUDIT_REPORT_PATH=/app/audit_report.html
MAX_ASSETS_PER_USER=5
HIGH_VALUE_THRESHOLD=50000
IDLE_DAYS_THRESHOLD=90
```

前端构建变量：

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## 当前说明

这是一个工程化原型到可运行系统的版本，已具备容器化部署、基础鉴权、前后端联调和主要 ITAM 流程。真实生产使用前建议继续补充：

- 正式 JWT / Session 机制
- 密码哈希与账号锁定
- 真实 LDAP / OIDC / SAML 登录流程
- 数据库迁移工具，如 Alembic
- 更细粒度 RBAC 权限
- 文件附件、二维码、导出报表
- CI/CD 与生产环境配置
