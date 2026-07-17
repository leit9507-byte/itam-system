"""remove Feishu approval workflow states

Revision ID: 20260717_0013
Revises: 20260716_0012
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa


revision = "20260717_0013"
down_revision = "20260716_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "purchases" in tables:
        bind.execute(
            sa.text(
                "UPDATE purchases SET status = 'pending_acceptance' "
                "WHERE status = 'approval_submitted'"
            )
        )

    if "repair_records" in tables:
        bind.execute(
            sa.text(
                "UPDATE repair_records SET status = :repairing "
                "WHERE status = 'approval_submitted'"
            ),
            {"repairing": "维修中"},
        )

    if {"assets", "repair_records"}.issubset(tables):
        bind.execute(
            sa.text(
                "UPDATE assets SET status = 'repair' "
                "WHERE asset_id IN ("
                "SELECT asset_id FROM repair_records WHERE status = :repairing"
                ") AND status NOT IN ('scrapped', 'disposed', 'repair')"
            ),
            {"repairing": "维修中"},
        )


def downgrade() -> None:
    # The original approval state cannot be reconstructed after normal work continues.
    pass
