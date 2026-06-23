# 资产管理系统

一套轻量级企业资产管理系统，包含资产台账、状态流转、流程审计、统计分析和 CSV 导出。当前版本采用原生前端 + Node.js 内置 HTTP 服务 + JSON 文件持久化，便于演示、二次开发和后续替换数据库。

## 快速启动

```bash
npm start
```

启动后访问：

```text
http://localhost:3000
```

也可以运行语法检查：

```bash
npm run check
```

## 系统模块

- 总览：资产总数、资产净值、在用资产、待处理事项、状态分布、近期变更。
- 资产台账：资产搜索、分类筛选、状态筛选、新增、编辑、状态流转、报废、CSV 导出。
- 流程记录：维修、闲置、报废等待关注事项，以及新增、编辑、状态变更审计。
- 统计分析：分类价值排行、折旧与风险提醒。

## 技术设计

### 前端

- `index.html`：页面结构和业务区域。
- `styles.css`：响应式布局、表格、卡片、弹窗、状态标识。
- `app.js`：前端状态管理、接口调用、渲染、表单提交、导出。

前端通过 `/api/assets`、`/api/assets/:id`、`/api/assets/:id/status` 与后端通信，不再依赖浏览器本地存储。

### 后端

- `server.js`：静态资源服务、REST API、参数校验、审计日志、JSON 持久化。
- `data/assets.json`：资产与审计日志数据源。

后端保持零第三方依赖，适合在没有安装依赖的环境中直接运行。后续可以平滑替换为 Express/Koa + SQLite/MySQL/PostgreSQL。

## API 设计

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 服务健康检查 |
| GET | `/api/assets` | 获取资产列表与审计日志 |
| POST | `/api/assets` | 新增资产 |
| PUT | `/api/assets/:id` | 更新资产档案 |
| PATCH | `/api/assets/:id/status` | 更新资产状态 |

## 数据模型

资产字段：

- `id`：系统 ID。
- `code`：资产编号，唯一。
- `name`：资产名称。
- `category`：资产分类。
- `status`：在用、闲置、借出、维修、报废。
- `owner`：负责人或部门。
- `location`：存放位置。
- `purchaseDate`：购置日期。
- `value`：资产价值。
- `notes`：备注。
- `createdAt` / `updatedAt`：创建与更新时间。

审计字段：

- `id`：审计 ID。
- `assetCode` / `assetName`：关联资产。
- `action`：操作类型。
- `actor`：操作者。
- `detail`：操作详情。
- `createdAt`：发生时间。

## 后续可扩展方向

- 用户、角色、权限：管理员、资产专员、部门负责人、普通员工。
- 审批流程：采购入库、领用、借用、归还、维修、报废。
- 附件管理：发票、合同、照片、维修单。
- 数据库：SQLite 适合单机部署，PostgreSQL/MySQL 适合多人协作。
- 登录认证：Session 或 JWT。
- 导入能力：Excel/CSV 批量导入资产。
- 盘点能力：二维码、盘点任务、差异报告。
