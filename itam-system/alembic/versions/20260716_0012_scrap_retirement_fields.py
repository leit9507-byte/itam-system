"""add scrap retirement registration fields

Revision ID: 20260716_0012
Revises: 20260716_0011
Create Date: 2026-07-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20260716_0012"
down_revision = "20260716_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    add_column("scrap_requests", sa.Column("retirement_date", sa.DateTime(), nullable=True))
    add_column("scrap_requests", sa.Column("retirement_approval_no", sa.String(length=128), nullable=True))


def downgrade() -> None:
    drop_column("scrap_requests", "retirement_approval_no")
    drop_column("scrap_requests", "retirement_date")


def add_column(table_name: str, column: sa.Column) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return
    columns = {item["name"] for item in inspector.get_columns(table_name)}
    if column.name not in columns:
        op.add_column(table_name, column)


def drop_column(table_name: str, column_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return
    columns = {item["name"] for item in inspector.get_columns(table_name)}
    if column_name in columns:
        op.drop_column(table_name, column_name)
