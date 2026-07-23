"""remove pending purchase from asset statuses

Revision ID: 20260723_0024
Revises: 20260722_0023
Create Date: 2026-07-23
"""

from alembic import op
import sqlalchemy as sa


revision = "20260723_0024"
down_revision = "20260722_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "assets" in inspector.get_table_names():
        op.execute("UPDATE assets SET status = 'pending_acceptance' WHERE status = 'pending_purchase'")


def downgrade() -> None:
    pass
