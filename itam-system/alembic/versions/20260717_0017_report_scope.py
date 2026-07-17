"""scope archived audit reports

Revision ID: 20260717_0017
Revises: 20260717_0016
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa


revision = "20260717_0017"
down_revision = "20260717_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("audit_report_archives")}
    if "scope_key" not in columns:
        op.add_column("audit_report_archives", sa.Column("scope_key", sa.String(length=160), nullable=False, server_default="global"))
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("audit_report_archives")}
    if "ix_audit_report_archives_scope_key" not in indexes:
        op.create_index("ix_audit_report_archives_scope_key", "audit_report_archives", ["scope_key"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("audit_report_archives")}
    if "ix_audit_report_archives_scope_key" in indexes:
        op.drop_index("ix_audit_report_archives_scope_key", table_name="audit_report_archives")
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("audit_report_archives")}
    if "scope_key" in columns:
        op.drop_column("audit_report_archives", "scope_key")
