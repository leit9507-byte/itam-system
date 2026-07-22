"""add retirement flow number to scrap requests

Revision ID: 20260722_0023
Revises: 20260722_0022
Create Date: 2026-07-22
"""

from alembic import op
import sqlalchemy as sa


revision = "20260722_0023"
down_revision = "20260722_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "scrap_requests" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("scrap_requests")}
    if "retirement_flow_no" not in columns:
        op.add_column("scrap_requests", sa.Column("retirement_flow_no", sa.String(length=64), nullable=True))
    indexes = {index["name"] for index in inspector.get_indexes("scrap_requests")}
    if "ix_scrap_requests_retirement_flow_no" not in indexes:
        op.create_index("ix_scrap_requests_retirement_flow_no", "scrap_requests", ["retirement_flow_no"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "scrap_requests" not in inspector.get_table_names():
        return
    indexes = {index["name"] for index in inspector.get_indexes("scrap_requests")}
    if "ix_scrap_requests_retirement_flow_no" in indexes:
        op.drop_index("ix_scrap_requests_retirement_flow_no", table_name="scrap_requests")
    columns = {column["name"] for column in inspector.get_columns("scrap_requests")}
    if "retirement_flow_no" in columns:
        op.drop_column("scrap_requests", "retirement_flow_no")
