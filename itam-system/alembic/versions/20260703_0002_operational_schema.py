"""operational schema additions

Revision ID: 20260703_0002
Revises: 20260623_0001
Create Date: 2026-07-03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260703_0002"
down_revision = "20260623_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    ensure_notification_settings(inspector)
    ensure_repair_fault_types(inspector)

    add_column(inspector, "user_directory", sa.Column("password_hash", sa.String(255), nullable=True))
    add_column(inspector, "user_directory", sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"))
    add_column(inspector, "user_directory", sa.Column("locked_until", sa.DateTime(), nullable=True))
    add_column(inspector, "user_directory", sa.Column("last_login_at", sa.DateTime(), nullable=True))

    add_column(inspector, "purchases", sa.Column("company", sa.String(128), nullable=True))
    add_column(inspector, "purchases", sa.Column("approval_no", sa.String(128), nullable=True))
    add_column(inspector, "purchases", sa.Column("supplier_name", sa.String(128), nullable=True))
    add_column(inspector, "purchases", sa.Column("purchase_reason", sa.Text(), nullable=True))
    add_column(inspector, "purchases", sa.Column("created_at", sa.DateTime(), nullable=True))
    if has_table(inspector, "purchases"):
        op.execute("UPDATE purchases SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")

    add_column(inspector, "purchase_items", sa.Column("retirement_years", sa.Integer(), nullable=True))
    add_column(inspector, "purchase_items", sa.Column("purchase_reason", sa.Text(), nullable=True))

    add_column(inspector, "product_catalogs", sa.Column("retirement_years", sa.Integer(), nullable=True))

    add_column(inspector, "assets", sa.Column("company", sa.String(128), nullable=True))
    add_column(inspector, "assets", sa.Column("purchase_date", sa.DateTime(), nullable=True))
    add_column(inspector, "assets", sa.Column("purchase_approval_no", sa.String(128), nullable=True))
    add_column(inspector, "assets", sa.Column("purchase_supplier_name", sa.String(128), nullable=True))
    add_column(inspector, "assets", sa.Column("warranty_expire_date", sa.DateTime(), nullable=True))
    add_column(inspector, "assets", sa.Column("warranty_months", sa.Integer(), nullable=True))
    if has_table(inspector, "assets"):
        op.execute("UPDATE assets SET company = '未设置公司' WHERE company IS NULL OR company = ''")

    add_column(inspector, "audit_rules", sa.Column("scope_category", sa.String(64), nullable=True))
    add_column(inspector, "audit_rules", sa.Column("threshold_value", sa.Float(), nullable=True))
    add_column(inspector, "audit_rules", sa.Column("threshold_days", sa.Integer(), nullable=True))

    add_column(inspector, "lifecycles", sa.Column("remark", sa.Text(), nullable=True))
    add_column(inspector, "notification_settings", sa.Column("event_types", sa.JSON(), nullable=True))


def downgrade() -> None:
    # Additive production migrations are intentionally not auto-downgraded to avoid data loss.
    pass


def has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def has_column(inspector, table_name: str, column_name: str) -> bool:
    if not has_table(inspector, table_name):
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def add_column(inspector, table_name: str, column: sa.Column) -> None:
    if has_column(inspector, table_name, column.name):
        return
    if not has_table(inspector, table_name):
        return
    op.add_column(table_name, column)


def ensure_notification_settings(inspector) -> None:
    if has_table(inspector, "notification_settings"):
        return
    op.create_table(
        "notification_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("channel", sa.String(64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("webhook_url", sa.String(512), nullable=True),
        sa.Column("secret", sa.String(255), nullable=True),
        sa.Column("event_types", sa.JSON(), nullable=True),
        sa.Column("last_test_status", sa.String(32), nullable=True),
        sa.Column("last_test_message", sa.String(255), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("channel", name="uq_notification_settings_channel"),
    )


def ensure_repair_fault_types(inspector) -> None:
    if has_table(inspector, "repair_fault_types"):
        return
    op.create_table(
        "repair_fault_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("enabled", sa.String(16), nullable=False, server_default="启用"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("name", name="uq_repair_fault_types_name"),
    )
