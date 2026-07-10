"""add scrap disposal fields

Revision ID: 20260708_0005
Revises: 20260708_0004
Create Date: 2026-07-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_0005"
down_revision = "20260708_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    add_column("scrap_requests", sa.Column("final_residual_value", sa.Float(), server_default="0", nullable=True))
    add_column("scrap_requests", sa.Column("disposal_remark", sa.Text(), nullable=True))
    add_column("scrap_requests", sa.Column("disposed_by", sa.String(length=128), nullable=True))
    add_column("scrap_requests", sa.Column("disposed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("scrap_requests", "disposed_at")
    op.drop_column("scrap_requests", "disposed_by")
    op.drop_column("scrap_requests", "disposal_remark")
    op.drop_column("scrap_requests", "final_residual_value")


def add_column(table_name: str, column: sa.Column) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return
    columns = {item["name"] for item in inspector.get_columns(table_name)}
    if column.name not in columns:
        op.add_column(table_name, column)
