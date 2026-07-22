"""add system settings table

Revision ID: 20260722_0022
Revises: 20260721_0021
Create Date: 2026-07-22
"""

from alembic import op
import sqlalchemy as sa


revision = "20260722_0022"
down_revision = "20260721_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "system_settings" not in inspector.get_table_names():
        op.create_table(
            "system_settings",
            sa.Column("key", sa.String(length=128), nullable=False),
            sa.Column("value", sa.Text(), nullable=False),
            sa.Column("updated_by", sa.String(length=128), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("key"),
        )
        op.create_index(op.f("ix_system_settings_key"), "system_settings", ["key"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "system_settings" in inspector.get_table_names():
        op.drop_index(op.f("ix_system_settings_key"), table_name="system_settings")
        op.drop_table("system_settings")
