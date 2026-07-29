"""add stocktake asset reconciliation fields

Revision ID: 20260729_0025
Revises: 20260723_0024
Create Date: 2026-07-29
"""

from alembic import op
import sqlalchemy as sa


revision = "20260729_0025"
down_revision = "20260723_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "stocktake_items" not in inspector.get_table_names():
        return
    columns = {item["name"] for item in inspector.get_columns("stocktake_items")}
    if "book_owner_user_id" not in columns:
        op.add_column("stocktake_items", sa.Column("book_owner_user_id", sa.String(length=64), nullable=True))
    if "actual_owner_user_id" not in columns:
        op.add_column("stocktake_items", sa.Column("actual_owner_user_id", sa.String(length=64), nullable=True))
    if "asset_info_updated" not in columns:
        op.add_column(
            "stocktake_items",
            sa.Column("asset_info_updated", sa.Boolean(), server_default=sa.false(), nullable=False),
        )
    indexes = {item["name"] for item in inspector.get_indexes("stocktake_items")}
    if "ix_stocktake_items_book_owner_user_id" not in indexes:
        op.create_index(
            "ix_stocktake_items_book_owner_user_id",
            "stocktake_items",
            ["book_owner_user_id"],
            unique=False,
        )
    if "ix_stocktake_items_actual_owner_user_id" not in indexes:
        op.create_index(
            "ix_stocktake_items_actual_owner_user_id",
            "stocktake_items",
            ["actual_owner_user_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "stocktake_items" not in inspector.get_table_names():
        return
    columns = {item["name"] for item in inspector.get_columns("stocktake_items")}
    indexes = {item["name"] for item in inspector.get_indexes("stocktake_items")}
    if "ix_stocktake_items_actual_owner_user_id" in indexes:
        op.drop_index("ix_stocktake_items_actual_owner_user_id", table_name="stocktake_items")
    if "ix_stocktake_items_book_owner_user_id" in indexes:
        op.drop_index("ix_stocktake_items_book_owner_user_id", table_name="stocktake_items")
    if "asset_info_updated" in columns:
        op.drop_column("stocktake_items", "asset_info_updated")
    if "actual_owner_user_id" in columns:
        op.drop_column("stocktake_items", "actual_owner_user_id")
    if "book_owner_user_id" in columns:
        op.drop_column("stocktake_items", "book_owner_user_id")
