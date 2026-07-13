"""convert money columns from float to decimal(12,2)

Revision ID: 20260710_0010
Revises: 20260709_0009
Create Date: 2026-07-10
"""

from alembic import op
import sqlalchemy as sa


revision = "20260710_0010"
down_revision = "20260709_0009"
branch_labels = None
depends_on = None


MONEY_COLUMNS = [
    ("assets", "purchase_price", True),
    ("purchases", "total_amount", True),
    ("purchase_items", "unit_price", True),
    ("repair_records", "repair_cost", False),
    ("scrap_requests", "purchase_price", True),
    ("scrap_requests", "estimated_residual_value", True),
    ("scrap_requests", "final_residual_value", True),
    ("product_catalogs", "unit_price", True),
    ("inventory_items", "unit_cost", False),
    ("approval_rules", "min_amount", True),
    ("approval_rules", "max_amount", True),
]


def has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    for table_name, column_name, nullable in MONEY_COLUMNS:
        if not has_column(table_name, column_name):
            continue
        op.alter_column(
            table_name,
            column_name,
            existing_type=sa.Float(),
            type_=sa.Numeric(12, 2),
            existing_nullable=nullable,
        )


def downgrade() -> None:
    for table_name, column_name, nullable in MONEY_COLUMNS:
        if not has_column(table_name, column_name):
            continue
        op.alter_column(
            table_name,
            column_name,
            existing_type=sa.Numeric(12, 2),
            type_=sa.Float(),
            existing_nullable=nullable,
        )
