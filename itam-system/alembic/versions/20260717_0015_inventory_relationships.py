"""add license seat history and component installation relationships

Revision ID: 20260717_0015
Revises: 20260717_0014
Create Date: 2026-07-17
"""

from collections import defaultdict
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision = "20260717_0015"
down_revision = "20260717_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "inventory_license_seats" not in tables:
        create_license_seats_table()
    if "inventory_license_seat_history" not in tables:
        create_license_history_table()
    if "inventory_component_installations" not in tables:
        create_component_installations_table()
    backfill_relationships(bind)


def create_license_seats_table() -> None:
    op.create_table(
        "inventory_license_seats",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("inventory_items.id"), nullable=False),
        sa.Column("seat_code", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="available", nullable=False),
        sa.Column("assignee_user_id", sa.String(length=64), nullable=True),
        sa.Column("assignee_name", sa.String(length=128), nullable=True),
        sa.Column("dept_id", sa.String(length=64), nullable=True),
        sa.Column("asset_id", sa.String(length=64), sa.ForeignKey("assets.asset_id"), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=True),
        sa.Column("returned_at", sa.DateTime(), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("item_id", "seat_code", name="uq_inventory_license_seat_code"),
    )
    op.create_index("ix_inventory_license_seats_item_id", "inventory_license_seats", ["item_id"])
    op.create_index("ix_inventory_license_seats_status", "inventory_license_seats", ["status"])
    op.create_index("ix_inventory_license_seats_assignee", "inventory_license_seats", ["assignee_user_id"])
    op.create_index("ix_inventory_license_seats_asset", "inventory_license_seats", ["asset_id"])
    op.create_index("ix_inventory_license_seats_dept", "inventory_license_seats", ["dept_id"])


def create_license_history_table() -> None:
    op.create_table(
        "inventory_license_seat_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("seat_id", sa.Integer(), sa.ForeignKey("inventory_license_seats.id"), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("assignee_user_id", sa.String(length=64), nullable=True),
        sa.Column("assignee_name", sa.String(length=128), nullable=True),
        sa.Column("dept_id", sa.String(length=64), nullable=True),
        sa.Column("asset_id", sa.String(length=64), sa.ForeignKey("assets.asset_id"), nullable=True),
        sa.Column("operator", sa.String(length=64), server_default="system", nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_inventory_license_history_seat", "inventory_license_seat_history", ["seat_id"])
    op.create_index("ix_inventory_license_history_action", "inventory_license_seat_history", ["action"])
    op.create_index("ix_inventory_license_history_assignee", "inventory_license_seat_history", ["assignee_user_id"])
    op.create_index("ix_inventory_license_history_dept", "inventory_license_seat_history", ["dept_id"])
    op.create_index("ix_inventory_license_history_asset", "inventory_license_seat_history", ["asset_id"])
    op.create_index("ix_inventory_license_history_created", "inventory_license_seat_history", ["created_at"])


def create_component_installations_table() -> None:
    op.create_table(
        "inventory_component_installations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("inventory_items.id"), nullable=False),
        sa.Column("asset_id", sa.String(length=64), sa.ForeignKey("assets.asset_id"), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("dept_id", sa.String(length=64), nullable=True),
        sa.Column("installed_by", sa.String(length=64), server_default="system", nullable=False),
        sa.Column("installed_at", sa.DateTime(), nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("item_id", "asset_id", name="uq_inventory_component_asset"),
    )
    op.create_index("ix_inventory_component_item", "inventory_component_installations", ["item_id"])
    op.create_index("ix_inventory_component_asset", "inventory_component_installations", ["asset_id"])
    op.create_index("ix_inventory_component_dept", "inventory_component_installations", ["dept_id"])


def backfill_relationships(bind) -> None:
    metadata = sa.MetaData()
    items = sa.Table("inventory_items", metadata, autoload_with=bind)
    ledger = sa.Table("inventory_ledger", metadata, autoload_with=bind)
    seats = sa.Table("inventory_license_seats", metadata, autoload_with=bind)
    history = sa.Table("inventory_license_seat_history", metadata, autoload_with=bind)
    installations = sa.Table("inventory_component_installations", metadata, autoload_with=bind)
    assets = sa.Table("assets", metadata, autoload_with=bind)
    now = datetime.utcnow()
    asset_ids = set(bind.execute(sa.select(assets.c.asset_id)).scalars())

    inventory_rows = bind.execute(sa.select(items)).mappings().all()
    ledgers_by_item = defaultdict(list)
    for row in bind.execute(sa.select(ledger).order_by(ledger.c.created_at.asc(), ledger.c.id.asc())).mappings():
        ledgers_by_item[row["item_id"]].append(row)

    for item in inventory_rows:
        if item["item_type"] == "license":
            backfill_license_item(bind, items, seats, history, item, ledgers_by_item[item["id"]], asset_ids, now)
        elif item["item_type"] == "component":
            backfill_component_item(bind, installations, item, ledgers_by_item[item["id"]], asset_ids, now)


def backfill_license_item(bind, items, seats, history, item, ledger_rows, asset_ids, now) -> None:
    existed = bind.execute(sa.select(sa.func.count()).select_from(seats).where(seats.c.item_id == item["id"])).scalar() or 0
    if existed:
        return
    total = max(int(item.get("total_qty") or 0), int(item.get("assigned_qty") or 0))
    if total <= 0:
        return
    width = max(3, len(str(total)))
    bind.execute(
        seats.insert(),
        [
            {
                "item_id": item["id"],
                "seat_code": f"{item['code']}-{index:0{width}d}",
                "status": "available",
                "created_at": now,
                "updated_at": now,
            }
            for index in range(1, total + 1)
        ],
    )
    seat_rows = [dict(row) for row in bind.execute(sa.select(seats).where(seats.c.item_id == item["id"]).order_by(seats.c.id)).mappings()]
    for ledger_row in ledger_rows:
        action = ledger_row.get("action")
        if action not in {"assign", "return"}:
            continue
        quantity = max(int(ledger_row.get("quantity") or 1), 1)
        if action == "assign":
            candidates = [seat for seat in seat_rows if seat["status"] != "assigned"][:quantity]
            for seat in candidates:
                apply_migrated_seat_action(bind, seats, history, seat, ledger_row, "assign", asset_ids, now)
        else:
            candidates = [seat for seat in seat_rows if seat["status"] == "assigned" and seat_matches_ledger(seat, ledger_row)]
            candidates += [seat for seat in seat_rows if seat["status"] == "assigned" and seat not in candidates]
            for seat in candidates[:quantity]:
                apply_migrated_seat_action(bind, seats, history, seat, ledger_row, "return", asset_ids, now)

    target_assigned = min(int(item.get("assigned_qty") or 0), total)
    assigned = [seat for seat in seat_rows if seat["status"] == "assigned"]
    if len(assigned) < target_assigned:
        for seat in [row for row in seat_rows if row["status"] != "assigned"][: target_assigned - len(assigned)]:
            migrated = {"created_at": now, "operator": "migration", "remark": "从原库存已分配数量迁移"}
            apply_migrated_seat_action(bind, seats, history, seat, migrated, "assign", asset_ids, now)
    elif len(assigned) > target_assigned:
        for seat in assigned[target_assigned:]:
            migrated = {"created_at": now, "operator": "migration", "remark": "按原库存当前数量校准"}
            apply_migrated_seat_action(bind, seats, history, seat, migrated, "return", asset_ids, now)
    bind.execute(items.update().where(items.c.id == item["id"]).values(total_qty=total, assigned_qty=target_assigned, available_qty=total - target_assigned))


def apply_migrated_seat_action(bind, seats, history, seat, ledger_row, action, asset_ids, now) -> None:
    occurred_at = ledger_row.get("created_at") or now
    asset_id = ledger_row.get("asset_id") if ledger_row.get("asset_id") in asset_ids else None
    snapshot = {
        "assignee_user_id": ledger_row.get("assignee_user_id") or seat.get("assignee_user_id"),
        "assignee_name": ledger_row.get("assignee_name") or seat.get("assignee_name"),
        "dept_id": ledger_row.get("dept_id") or seat.get("dept_id"),
        "asset_id": asset_id or seat.get("asset_id"),
    }
    if action == "assign":
        values = {**snapshot, "status": "assigned", "assigned_at": occurred_at, "returned_at": None, "remark": ledger_row.get("remark"), "updated_at": occurred_at}
    else:
        values = {"status": "recovered", "assignee_user_id": None, "assignee_name": None, "dept_id": None, "asset_id": None, "assigned_at": None, "returned_at": occurred_at, "remark": ledger_row.get("remark"), "updated_at": occurred_at}
    bind.execute(seats.update().where(seats.c.id == seat["id"]).values(**values))
    bind.execute(
        history.insert().values(
            seat_id=seat["id"],
            action=action,
            operator=ledger_row.get("operator") or "migration",
            remark=ledger_row.get("remark"),
            created_at=occurred_at,
            **snapshot,
        )
    )
    seat.update(values)


def seat_matches_ledger(seat, ledger_row) -> bool:
    for key in ("assignee_user_id", "asset_id"):
        if ledger_row.get(key) and seat.get(key) != ledger_row.get(key):
            return False
    return True


def backfill_component_item(bind, installations, item, ledger_rows, asset_ids, now) -> None:
    existed = bind.execute(sa.select(sa.func.count()).select_from(installations).where(installations.c.item_id == item["id"])).scalar() or 0
    if existed:
        return
    current = {}
    for row in ledger_rows:
        action = row.get("action")
        asset_id = row.get("asset_id")
        if action not in {"install", "uninstall"} or asset_id not in asset_ids:
            continue
        entry = current.setdefault(asset_id, {"quantity": 0, "row": row})
        amount = max(int(row.get("quantity") or 1), 1)
        entry["quantity"] += amount if action == "install" else -amount
        entry["row"] = row
    values = []
    for asset_id, entry in current.items():
        if entry["quantity"] <= 0:
            continue
        row = entry["row"]
        values.append(
            {
                "item_id": item["id"],
                "asset_id": asset_id,
                "quantity": entry["quantity"],
                "dept_id": row.get("dept_id") or item.get("dept_id"),
                "installed_by": row.get("operator") or "migration",
                "installed_at": row.get("created_at") or now,
                "remark": row.get("remark"),
                "updated_at": row.get("created_at") or now,
            }
        )
    if values:
        bind.execute(installations.insert(), values)


def downgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "inventory_component_installations" in tables:
        op.drop_table("inventory_component_installations")
    if "inventory_license_seat_history" in tables:
        op.drop_table("inventory_license_seat_history")
    if "inventory_license_seats" in tables:
        op.drop_table("inventory_license_seats")
