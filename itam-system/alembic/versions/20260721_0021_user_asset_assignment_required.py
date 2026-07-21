"""track users that do not require onboarding asset assignment

Revision ID: 20260721_0021
Revises: 20260721_0020
Create Date: 2026-07-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260721_0021"
down_revision = "20260721_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "user_directory" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("user_directory")}
    if "asset_assignment_required" not in columns:
        op.add_column(
            "user_directory",
            sa.Column("asset_assignment_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "user_directory" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("user_directory")}
    if "asset_assignment_required" in columns:
        op.drop_column("user_directory", "asset_assignment_required")
