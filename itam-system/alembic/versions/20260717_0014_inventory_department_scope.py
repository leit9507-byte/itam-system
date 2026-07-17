"""add inventory department scope

Revision ID: 20260717_0014
Revises: 20260717_0013
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa


revision = "20260717_0014"
down_revision = "20260717_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "inventory_items" not in tables:
        return
    columns = {item["name"] for item in inspector.get_columns("inventory_items")}
    if "dept_id" not in columns:
        op.add_column("inventory_items", sa.Column("dept_id", sa.String(length=64), nullable=True))
    indexes = {item["name"] for item in inspector.get_indexes("inventory_items")}
    if "ix_inventory_items_dept_id" not in indexes:
        op.create_index("ix_inventory_items_dept_id", "inventory_items", ["dept_id"], unique=False)
    if "inventory_ledger" in tables:
        bind.execute(
            sa.text(
                "UPDATE inventory_items SET dept_id = ("
                "SELECT MIN(ledger.dept_id) FROM inventory_ledger AS ledger "
                "WHERE ledger.item_id = inventory_items.id "
                "AND ledger.dept_id IS NOT NULL AND ledger.dept_id <> '' "
                "HAVING COUNT(DISTINCT ledger.dept_id) = 1"
                ") WHERE dept_id IS NULL"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "inventory_items" not in inspector.get_table_names():
        return
    columns = {item["name"] for item in inspector.get_columns("inventory_items")}
    if "dept_id" in columns:
        indexes = {item["name"] for item in inspector.get_indexes("inventory_items")}
        if "ix_inventory_items_dept_id" in indexes:
            op.drop_index("ix_inventory_items_dept_id", table_name="inventory_items")
        op.drop_column("inventory_items", "dept_id")
