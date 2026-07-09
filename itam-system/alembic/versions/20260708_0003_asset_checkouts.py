"""asset checkout records

Revision ID: 20260708_0003
Revises: 20260703_0002
Create Date: 2026-07-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_0003"
down_revision = "20260703_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "asset_checkouts" in inspector.get_table_names():
        return
    op.create_table(
        "asset_checkouts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("asset_id", sa.String(64), sa.ForeignKey("assets.asset_id"), nullable=False),
        sa.Column("checkout_type", sa.String(32), nullable=False),
        sa.Column("assignee_user_id", sa.String(64), nullable=True),
        sa.Column("assignee_name", sa.String(128), nullable=True),
        sa.Column("dept_id", sa.String(64), nullable=True),
        sa.Column("location", sa.String(128), nullable=True),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("checked_out_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("checked_out_by", sa.String(64), nullable=False, server_default="system"),
        sa.Column("checked_in_at", sa.DateTime(), nullable=True),
        sa.Column("checked_in_by", sa.String(64), nullable=True),
        sa.Column("checkin_location", sa.String(128), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("checkin_remark", sa.Text(), nullable=True),
    )
    op.create_index("ix_asset_checkouts_asset_id", "asset_checkouts", ["asset_id"])
    op.create_index("ix_asset_checkouts_status", "asset_checkouts", ["status"])
    op.create_index("ix_asset_checkouts_checkout_type", "asset_checkouts", ["checkout_type"])
    op.create_index("ix_asset_checkouts_assignee_user_id", "asset_checkouts", ["assignee_user_id"])
    op.create_index("ix_asset_checkouts_dept_id", "asset_checkouts", ["dept_id"])


def downgrade() -> None:
    op.drop_table("asset_checkouts")
