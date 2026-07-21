"""create missing master tables for clean deployments

Revision ID: 20260721_0019
Revises: 20260717_0018
Create Date: 2026-07-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260721_0019"
down_revision = "20260717_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "companies" not in tables:
        op.create_table(
            "companies",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("code", sa.String(length=64), nullable=True),
            sa.Column("contact", sa.String(length=128), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="启用"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("name", name="uq_companies_name"),
        )
        op.create_index("ix_companies_id", "companies", ["id"])
        op.create_index("ix_companies_name", "companies", ["name"])
        op.create_index("ix_companies_code", "companies", ["code"])

    if "locations" not in tables:
        op.create_table(
            "locations",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("code", sa.String(length=64), nullable=True),
            sa.Column("type", sa.String(length=64), nullable=False, server_default="办公位置"),
            sa.Column("owner_dept", sa.String(length=128), nullable=True),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="启用"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("name", name="uq_locations_name"),
        )
        op.create_index("ix_locations_id", "locations", ["id"])
        op.create_index("ix_locations_name", "locations", ["name"])
        op.create_index("ix_locations_code", "locations", ["code"])
        op.create_index("ix_locations_type", "locations", ["type"])
        op.create_index("ix_locations_status", "locations", ["status"])

    if "scrap_requests" not in tables:
        op.create_table(
            "scrap_requests",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("request_no", sa.String(length=64), nullable=False),
            sa.Column("asset_id", sa.String(length=64), nullable=False),
            sa.Column("asset_name", sa.String(length=128), nullable=False),
            sa.Column("asset_sn", sa.String(length=128), nullable=True),
            sa.Column("company", sa.String(length=128), nullable=True),
            sa.Column("category", sa.String(length=64), nullable=True),
            sa.Column("brand", sa.String(length=64), nullable=True),
            sa.Column("model", sa.String(length=64), nullable=True),
            sa.Column("owner_user_id", sa.String(length=64), nullable=True),
            sa.Column("dept_id", sa.String(length=64), nullable=True),
            sa.Column("location", sa.String(length=128), nullable=True),
            sa.Column("purchase_price", sa.Numeric(12, 2, asdecimal=False), nullable=True, server_default="0"),
            sa.Column("purchase_date", sa.DateTime(), nullable=True),
            sa.Column("purchase_approval_no", sa.String(length=128), nullable=True),
            sa.Column("purchase_supplier_name", sa.String(length=128), nullable=True),
            sa.Column("applicant", sa.String(length=128), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("disposal_method", sa.String(length=64), nullable=True),
            sa.Column("retirement_date", sa.DateTime(), nullable=True),
            sa.Column("retirement_approval_no", sa.String(length=128), nullable=True),
            sa.Column("estimated_residual_value", sa.Numeric(12, 2, asdecimal=False), nullable=True, server_default="0"),
            sa.Column("final_residual_value", sa.Numeric(12, 2, asdecimal=False), nullable=True, server_default="0"),
            sa.Column("disposal_remark", sa.Text(), nullable=True),
            sa.Column("dispose_recipient_user_id", sa.String(length=128), nullable=True),
            sa.Column("dispose_recipient_name", sa.String(length=128), nullable=True),
            sa.Column("disposed_by", sa.String(length=128), nullable=True),
            sa.Column("disposed_at", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="待处置"),
            sa.Column("approver", sa.String(length=128), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("request_no", name="uq_scrap_requests_request_no"),
        )
        op.create_index("ix_scrap_requests_id", "scrap_requests", ["id"])
        op.create_index("ix_scrap_requests_request_no", "scrap_requests", ["request_no"])
        op.create_index("ix_scrap_requests_asset_id", "scrap_requests", ["asset_id"])
        op.create_index("ix_scrap_requests_status", "scrap_requests", ["status"])


def downgrade() -> None:
    pass
