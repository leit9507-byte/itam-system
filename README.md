# ITAM 企业 IT 资产管理系统

一套可容器化部署的企业 IT 资产管理系统，围绕资产从采购验收、入库、借用、维修、盘点到退役处置的完整生命周期建设，同时管理软件许可席位、耗材、配件和组件。

当前产品不提供 OIDC/SAML 或飞书登录，不对接飞书审批。登录方式仅包含本地账户和 LDAP；飞书能力仅用于移动端 JSAPI 签名及 Webhook 消息通知。

## 产品范围

### 资产管理

- 资产台账、搜索、筛选、分页和批量导入
- 资产编号、序列号、产品档案、采购审批单号、供应商、价值、当前残值和退役年限
- 当前残值按采购日期和退役年限进行直线折旧，默认净残值率为 5%；缺少折旧依据时按采购原值显示
- 入库、出库到人员或地址、借用、归还、维修、盘点和报废处置
- 资产详情编辑、风险提示、附件和完整生命周期时间线
- 生命周期按领用归还、字段变更、维修报废等类型筛选
- 在用、在库、闲置、借出、维修、待报废、待处置和已报废等状态管理

### 采购与产品档案

- 创建采购单并维护采购审批单号、供应商和采购明细
- 采购单直接进入验收入库，不在系统内执行采购审批
- 验收时逐台填写序列号、部门、责任人、地址和仓库
- 验收完成后生成资产，并保留采购单号和采购审批单号
- 产品档案与设备类型独立维护
- 产品名称、品牌、型号、规格、默认仓库、单价和退役年限可带入资产

### 借用中心

- 专门登记设备临时借用，不代替资产台账中的“在用”状态
- 记录借用人、借用时间、计划归还时间、实际归还时间和备注
- 提供借用中、即将到期、逾期未归还和已归还统计
- 支持批量借用和批量归还

### 维修管理

- 维修工单、故障类型、维修类型、供应商、费用和附件
- 支持维修完成、无法修复、在保维修等处理结果
- 维修结束后同步资产状态和生命周期
- 提供型号故障数量、品牌故障率和设备服役年限故障趋势

### 软件许可与配件管理

- 软件许可维护授权总量、到期时间和供应商
- 每个授权席位具有独立编号、当前状态、绑定人员和绑定资产
- 席位支持分配、回收、停用和恢复，并保留完整历史
- 耗材和配件维护库存数量、领用流水和低库存提醒
- 组件装配到资产时建立稳定的当前安装关系
- 组件拆卸后同步当前安装关系和库存流水

### 盘点、审计与报表

- 后台创建盘点任务并固化盘点范围
- 移动端只选择进行中的盘点任务并扫码执行
- 记录盘盈、盘亏、位置不符和使用人不符等差异
- 审计中心支持手动审计、故障设备审计和超期服役分析
- 操作日志和错误日志统一在日志中心查看
- 审计报告在报告中心生成、预览和历史留档
- 支持部门资产、人员持有、逾期借用、即将过保和报废处置台账导出

## 当前业务规则

### 登录与飞书

- 本地账户使用用户名和密码登录
- LDAP 身份源可配置、测试、登录和定时同步用户目录
- 每次完整 LDAP 同步会与该身份源现有在职账号比较；本次结果中不存在的账号保留档案并标记为离职
- 离职账号不能登录，名下资产通过离职回收待办处理，不会在同步时自动修改资产状态
- 不提供 OIDC、SAML、飞书登录或飞书免登
- 飞书 JSAPI 签名仅用于飞书客户端内的扫码能力
- 飞书 Webhook 仅用于业务事件通知
- 飞书应用审批和飞书用户同步不属于当前产品范围

### 二维码识别

系统不在资产详情中生成或展示资产二维码。资产详情的“二维码绑定”用于保存外部二维码扫码后返回的原始文字：

1. 扫描已有设备标签，取得二维码原始内容。
2. 在资产详情中将该文字绑定到资产。
3. 一台资产可以绑定多个二维码内容。
4. 后续移动端扫描任一已绑定内容，都可解析到对应资产。
5. 更换标签格式时可新增绑定或解绑旧内容，不需要修改资产编号。

### 报废处置

系统不执行报废审批流。退役审批在外部完成后，本系统只登记和归档结果：

1. 资产提交报废处置登记后进入“待处置登记”。
2. 实际处置完成时填写退役时间和外部退役审批单号。
3. 处理手段必须选择“报废”“变卖”或“员工领用”。
4. 员工领用表示员工领走报废资产，需要选择领走员工。
5. 同时登记实际残值和处置说明。
6. 完成后资产进入处置终态，不能再入库、借用、维修或参加普通盘点。

## 技术栈

后端：Python 3.11、FastAPI、SQLAlchemy、MySQL 8.0、Pydantic、Alembic、Uvicorn。

前端：Vue 3、Vite、Element Plus、Vue Router、Pinia、Axios、ECharts、Nginx。

部署：Docker Compose、MySQL、FastAPI 后端和 Nginx 静态前端。

## 快速启动

开发或本机演示环境：

```powershell
.\scripts\container-deploy.ps1 -Rebuild
```

也可以直接运行：

```powershell
docker compose -p itam up --build -d
```

默认访问地址：

- 前端：http://127.0.0.1:5173
- 后端 API：http://127.0.0.1:8000
- API 文档：http://127.0.0.1:8000/docs
- MySQL：127.0.0.1:3306

停止服务：

```powershell
docker compose -p itam down
```

重置数据库会删除现有业务数据，只能用于开发环境：

```powershell
.\scripts\container-deploy.ps1 -Rebuild -ResetData
```

生产环境部署、迁移、备份和恢复请参阅 [PRODUCTION.md](PRODUCTION.md)。

## 默认账号

首次初始化会创建本地管理员和审计员：

| 角色 | 账号 | 初始密码 | 登录方式 |
| --- | --- | --- | --- |
| 管理员 | `admin` | `admin` | 本地账户 |
| 审计员 | `auditor` | `auditor` | 本地账户 |

首次登录后必须立即修改默认密码，生产环境不得继续使用初始密码。

## 安全与权限

- Bearer JWT 登录令牌和会话过期
- PBKDF2 密码哈希、登录失败计数和账号自动锁定
- 前端路由守卫和后端接口鉴权中间件
- 管理员、资产管理员、部门负责人、审计员和普通员工角色
- 基于角色、资源和动作的 RBAC 权限
- 资产、采购、维修、借用、盘点、库存关系和报表的数据范围控制
- 关键业务操作写入审计日志
- 附件上传类型、大小、下载权限和持久化目录控制

未登录访问业务 API 会返回 `401`。普通员工只能查看与本人相关的数据，部门负责人只能访问本部门范围。

## 常用 API

### 登录与用户

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/auth/login` | 本地账户或 LDAP 登录并返回 JWT |
| GET | `/auth/me/permissions` | 当前用户角色和资源权限 |
| GET | `/users/list` | 用户目录 |
| POST | `/users/save` | 新增或修改本地用户 |
| POST | `/users/sync` | 执行 LDAP 用户同步 |
| GET | `/identity/providers` | LDAP 身份源列表 |
| POST | `/identity/providers` | 新增 LDAP 身份源 |
| POST | `/identity/providers/{id}/test` | 测试 LDAP 配置 |

### 资产与二维码绑定

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/asset/list` | 资产列表 |
| POST | `/asset/create` | 创建资产 |
| PUT | `/asset/{asset_id}` | 更新资产信息 |
| POST | `/asset/import/text` | CSV 或表格文本批量导入 |
| GET | `/scan-bindings/asset/{asset_id}` | 查询资产已绑定二维码内容 |
| POST | `/scan-bindings/asset/{asset_id}` | 绑定二维码原始内容 |
| DELETE | `/scan-bindings/{binding_id}` | 解绑二维码内容 |
| POST | `/scan-bindings/resolve` | 根据扫码原文解析资产 |
| GET | `/scan-bindings/feishu-jsapi-signature` | 获取飞书 JSAPI 签名 |

### 采购、库存与处置

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/purchase/list` | 采购单列表 |
| POST | `/purchase/create` | 创建采购单 |
| POST | `/purchase/accept?purchase_no=...` | 验收明细并生成资产 |
| GET | `/inventory/items` | 软件许可、耗材、配件和组件列表 |
| GET | `/inventory/items/{id}/license-seats` | 软件授权席位列表 |
| POST | `/inventory/license-seats/{id}/assign` | 分配授权席位 |
| POST | `/inventory/license-seats/{id}/return` | 回收授权席位 |
| GET | `/inventory/items/{id}/installations` | 组件当前安装关系 |
| GET | `/scrap/list` | 报废处置登记列表 |
| POST | `/scrap/{asset_id}/create` | 提交待处置登记 |
| POST | `/scrap/{id}/dispose` | 登记实际退役和处置结果 |

### 文件、通知与报表

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/files/asset/{asset_id}/upload` | 上传资产附件 |
| GET | `/files/asset/{asset_id}` | 资产附件列表 |
| GET | `/files/{file_id}/download` | 鉴权下载附件 |
| GET | `/notification/settings` | 飞书 Webhook 通知配置 |
| POST | `/notification/test` | 发送测试通知 |
| GET | `/reports/assets.csv` | 导出资产清单 |
| GET | `/reports/assets.pdf` | 导出资产 PDF |
| GET | `/reports/scrap-disposal-ledger.csv` | 导出报废处置台账 |

完整接口以运行环境的 `/docs` 为准。

## 数据库迁移

生产和开发环境都应使用 Alembic 管理数据库结构：

```powershell
cd itam-system
alembic upgrade head
```

创建新迁移：

```powershell
alembic revision --autogenerate -m "change description"
```

正式库禁止通过删除表或重置数据库代替迁移。升级前应完成数据库备份，并定期进行恢复演练。

## 开发模式

需要前后端热更新时：

```powershell
.\scripts\container-dev.ps1 -Rebuild
```

等价命令：

```powershell
docker compose -p itam -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

生产环境使用 Nginx 部署前端构建后的静态文件，后端关闭 reload。

## 项目结构

```text
.
├── docker-compose.yml
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── README.md
├── PRODUCTION.md
├── scripts/
├── itam-system/
│   ├── alembic/
│   └── app/
│       ├── api/
│       ├── core/
│       ├── models/
│       ├── schemas/
│       ├── services/
│       ├── rules/
│       └── reports/
└── itam-frontend/
    ├── nginx.conf
    └── src/
        ├── api/
        ├── components/
        ├── layout/
        ├── router/
        ├── store/
        └── views/
```

## 主要环境变量

```text
DATABASE_URL=mysql+pymysql://itam:itam_pass@mysql:3306/itam_system?charset=utf8mb4
JWT_SECRET=change-this-secret
JWT_EXPIRE_MINUTES=480
LOGIN_LOCK_THRESHOLD=5
LOGIN_LOCK_MINUTES=15
UPLOAD_DIR=/app/runtime/uploads
AUDIT_REPORT_PATH=/app/runtime/reports/audit_report.html
MAX_ASSETS_PER_USER=5
HIGH_VALUE_THRESHOLD=50000
IDLE_DAYS_THRESHOLD=90
ASSET_RESIDUAL_RATE=0.05
```

前端构建变量：

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```
