# 企业级 IT 资产管理系统（ITAM）

本项目是一个可运行的企业级 IT 资产管理后端，覆盖资产管理、采购入库自动生成资产、生命周期记录、规则引擎、审计引擎、风险评分和 HTML 审计报告。

## 技术栈

- Python 3.10+
- FastAPI
- SQLAlchemy ORM
- MySQL（通过 `DATABASE_URL` 配置）
- Pydantic
- Jinja2
- Uvicorn

本地未配置 MySQL 时，系统默认使用 `sqlite:///./itam.db`，便于直接启动验收。生产或联调 MySQL 时设置：

```bash
set DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/itam_system?charset=utf8mb4
```

## 启动

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

也可以：

```bash
python main.py
```

访问：

```text
http://127.0.0.1:8000/docs
```

## API

### Asset

- `POST /asset/create`
- `GET /asset/list`
- `POST /asset/{asset_id}/status`

创建资产示例：

```json
{
  "name": "MacBook Pro 14",
  "category": "Laptop",
  "brand": "Apple",
  "model": "M3 Pro",
  "sn": "SN-001",
  "config": {"cpu": "M3 Pro", "memory": "18GB"},
  "purchase_price": 16999,
  "status": "in_use",
  "owner_user_id": "u001",
  "dept_id": "D-RD",
  "location": "上海总部"
}
```

### Purchase

- `POST /purchase/create`
- `POST /purchase/receive?purchase_no=PO-2026-001`

采购创建示例：

```json
{
  "purchase_no": "PO-2026-001",
  "total_amount": 30000,
  "status": "created",
  "items": [
    {
      "name": "ThinkPad X1",
      "category": "Laptop",
      "brand": "Lenovo",
      "model": "X1",
      "quantity": 2,
      "unit_price": 15000,
      "location": "上海总部",
      "dept_id": "D-RD"
    }
  ]
}
```

当调用 `/purchase/receive` 后，系统会自动：

- 拆分采购明细数量；
- 生成资产编号；
- 写入 `assets`；
- 写入 `lifecycles`，动作类型为 `PURCHASE`；
- 将采购单状态更新为 `received`。

### Audit

- `POST /audit/run`
- `GET /audit/report`

审计结果示例：

```json
{
  "total_assets": 3,
  "violations": [],
  "risk_score": 0
}
```

## 规则引擎

已实现规则：

- 用户资产数量超限；
- 资产闲置超过 90 天；
- 高价值资产未绑定部门；
- 单人资产总值超过阈值。

输出格式：

```json
[
  {
    "asset_id": "ITAM-000001",
    "rule": "HIGH_VALUE_WITHOUT_DEPT",
    "severity": "high",
    "message": "高价值资产未绑定部门"
  }
]
```

## 审计风险评分

- `high = 30`
- `medium = 15`
- `low = 5`
- 最大分值 100

## 项目结构

```text
itam-system/
├── app/
│   ├── main.py
│   ├── core/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── rules/
│   ├── reports/
│   └── api/
├── main.py
├── requirements.txt
└── README.md
```
