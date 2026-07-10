"""add generic scan bindings

Revision ID: 20260709_0008
Revises: 20260708_0007
Create Date: 2026-07-09
"""

from alembic import op
import sqlalchemy as sa


revision = "20260709_0008"
down_revision = "20260708_0007"
branch_labels = None
depends_on = None


def has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def has_index(table_name: str, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in sa.inspect(op.get_bind()).get_indexes(table_name))


def upgrade() -> None:
    if not has_table("asset_scan_bindings"):
        op.create_table(
            "asset_scan_bindings",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("asset_id", sa.String(length=64), nullable=False),
            sa.Column("scan_key", sa.String(length=255), nullable=False),
            sa.Column("scan_raw", sa.Text(), nullable=False),
            sa.Column("scan_type", sa.String(length=64), nullable=False, server_default="generic"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(length=128), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    if not has_index("asset_scan_bindings", "ix_asset_scan_bindings_asset_id"):
        op.create_index("ix_asset_scan_bindings_asset_id", "asset_scan_bindings", ["asset_id"])
    if not has_index("asset_scan_bindings", "ux_asset_scan_bindings_scan_key"):
        op.create_index("ux_asset_scan_bindings_scan_key", "asset_scan_bindings", ["scan_key"], unique=True)
    if not has_index("asset_scan_bindings", "ix_asset_scan_bindings_status"):
        op.create_index("ix_asset_scan_bindings_status", "asset_scan_bindings", ["status"])


def downgrade() -> None:
    if has_table("asset_scan_bindings"):
        op.drop_table("asset_scan_bindings")
