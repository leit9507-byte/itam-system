"""add audit report archives

Revision ID: 20260709_0009
Revises: 20260709_0008
Create Date: 2026-07-09
"""

from alembic import op
import sqlalchemy as sa


revision = "20260709_0009"
down_revision = "20260709_0008"
branch_labels = None
depends_on = None


def has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def has_index(table_name: str, index_name: str) -> bool:
    return any(index.get("name") == index_name for index in sa.inspect(op.get_bind()).get_indexes(table_name))


def upgrade() -> None:
    if not has_table("audit_report_archives"):
        op.create_table(
            "audit_report_archives",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("report_no", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("report_type", sa.String(length=32), nullable=False, server_default="audit"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="generated"),
            sa.Column("total_assets", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("violation_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("html_path", sa.String(length=512), nullable=False),
            sa.Column("pdf_path", sa.String(length=512), nullable=True),
            sa.Column("xlsx_path", sa.String(length=512), nullable=True),
            sa.Column("created_by", sa.String(length=128), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    if not has_index("audit_report_archives", "ux_audit_report_archives_report_no"):
        op.create_index("ux_audit_report_archives_report_no", "audit_report_archives", ["report_no"], unique=True)
    if not has_index("audit_report_archives", "ix_audit_report_archives_created_at"):
        op.create_index("ix_audit_report_archives_created_at", "audit_report_archives", ["created_at"])


def downgrade() -> None:
    if has_table("audit_report_archives"):
        op.drop_table("audit_report_archives")
