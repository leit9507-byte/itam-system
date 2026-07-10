"""inventory items and ledger"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_0004"
down_revision = "20260708_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if "inventory_items" in tables and "inventory_ledger" in tables:
        return
    if "inventory_items" not in tables:
        op.create_table(
            "inventory_items",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("item_type", sa.String(length=32), nullable=False),
            sa.Column("code", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("brand", sa.String(length=64), nullable=True),
            sa.Column("model", sa.String(length=64), nullable=True),
            sa.Column("spec", sa.String(length=255), nullable=True),
            sa.Column("total_qty", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("available_qty", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("assigned_qty", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("min_qty", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("unit_cost", sa.Float(), nullable=False, server_default="0"),
            sa.Column("license_key", sa.String(length=255), nullable=True),
            sa.Column("expire_date", sa.DateTime(), nullable=True),
            sa.Column("supplier", sa.String(length=128), nullable=True),
            sa.Column("location", sa.String(length=128), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code"),
        )
        op.create_index("ix_inventory_items_item_type", "inventory_items", ["item_type"])
        op.create_index("ix_inventory_items_status", "inventory_items", ["status"])

    if "inventory_ledger" in tables:
        return
    op.create_table(
        "inventory_ledger",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("assignee_user_id", sa.String(length=64), nullable=True),
        sa.Column("assignee_name", sa.String(length=128), nullable=True),
        sa.Column("dept_id", sa.String(length=64), nullable=True),
        sa.Column("asset_id", sa.String(length=64), nullable=True),
        sa.Column("location", sa.String(length=128), nullable=True),
        sa.Column("operator", sa.String(length=64), nullable=False, server_default="system"),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.asset_id"]),
        sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_ledger_action", "inventory_ledger", ["action"])
    op.create_index("ix_inventory_ledger_item_id", "inventory_ledger", ["item_id"])


def downgrade() -> None:
    op.drop_table("inventory_ledger")
    op.drop_table("inventory_items")
