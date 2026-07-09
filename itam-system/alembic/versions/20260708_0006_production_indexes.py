"""production query indexes

Revision ID: 20260708_0006
Revises: 20260708_0005
Create Date: 2026-07-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_0006"
down_revision = "20260708_0005"
branch_labels = None
depends_on = None


def has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def create_index(index_name: str, table_name: str, columns: list[str]) -> None:
    if not has_index(table_name, index_name):
        op.create_index(index_name, table_name, columns)


def drop_index(index_name: str, table_name: str) -> None:
    if has_index(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)


def upgrade() -> None:
    create_index("ix_assets_location", "assets", ["location"])
    create_index("ix_assets_created_at", "assets", ["created_at"])
    create_index("ix_assets_status_created_at", "assets", ["status", "created_at"])
    create_index("ix_assets_owner_status", "assets", ["owner_user_id", "status"])
    create_index("ix_assets_dept_status", "assets", ["dept_id", "status"])
    create_index("ix_assets_location_status", "assets", ["location", "status"])

    create_index("ix_lifecycles_action_type", "lifecycles", ["action_type"])
    create_index("ix_lifecycles_timestamp", "lifecycles", ["timestamp"])
    create_index("ix_lifecycles_asset_timestamp", "lifecycles", ["asset_id", "timestamp"])

    create_index("ix_asset_attachments_created_at", "asset_attachments", ["created_at"])
    create_index("ix_asset_attachments_asset_status_created", "asset_attachments", ["asset_id", "status", "created_at"])

    create_index("ix_operation_audit_logs_module_created", "operation_audit_logs", ["module", "created_at"])
    create_index("ix_operation_audit_logs_operator_created", "operation_audit_logs", ["operator", "created_at"])

    create_index("ix_stocktake_tasks_status_created", "stocktake_tasks", ["status", "created_at"])
    create_index("ix_stocktake_items_task_result", "stocktake_items", ["task_id", "result"])
    create_index("ix_stocktake_items_task_asset", "stocktake_items", ["task_id", "asset_id"])


def downgrade() -> None:
    drop_index("ix_stocktake_items_task_asset", "stocktake_items")
    drop_index("ix_stocktake_items_task_result", "stocktake_items")
    drop_index("ix_stocktake_tasks_status_created", "stocktake_tasks")

    drop_index("ix_operation_audit_logs_operator_created", "operation_audit_logs")
    drop_index("ix_operation_audit_logs_module_created", "operation_audit_logs")

    drop_index("ix_asset_attachments_asset_status_created", "asset_attachments")
    drop_index("ix_asset_attachments_created_at", "asset_attachments")

    drop_index("ix_lifecycles_asset_timestamp", "lifecycles")
    drop_index("ix_lifecycles_timestamp", "lifecycles")
    drop_index("ix_lifecycles_action_type", "lifecycles")

    drop_index("ix_assets_location_status", "assets")
    drop_index("ix_assets_dept_status", "assets")
    drop_index("ix_assets_owner_status", "assets")
    drop_index("ix_assets_status_created_at", "assets")
    drop_index("ix_assets_created_at", "assets")
    drop_index("ix_assets_location", "assets")
