"""add concurrency-safe business number sequences

Revision ID: 20260717_0018
Revises: 20260717_0017
Create Date: 2026-07-17
"""

import re
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision = "20260717_0018"
down_revision = "20260717_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "number_sequences" not in inspector.get_table_names():
        op.create_table(
            "number_sequences",
            sa.Column("key", sa.String(length=64), primary_key=True),
            sa.Column("current_value", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
    op.alter_column(
        "number_sequences",
        "updated_at",
        existing_type=sa.DateTime(),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )

    bind = op.get_bind()
    seeds = [
        ("asset:ITAM", "assets", "asset_id", r"^ITAM-(\d+)$"),
        ("supplier", "suppliers", "supplier_no", r"^SUP-(\d+)$"),
    ]
    year = datetime.utcnow().year
    seeds.extend([
        (f"repair:{year}", "repair_records", "repair_no", rf"^RP-{year}-(\d+)$"),
        (f"scrap:{year}", "scrap_requests", "request_no", rf"^SC-{year}-(\d+)$"),
        (f"stocktake:{year}", "stocktake_tasks", "id", rf"^ST-{year}-(\d+)$"),
        (f"audit_report:{year}", "audit_report_archives", "report_no", rf"^AR-{year}-(\d+)$"),
    ])
    tables = set(sa.inspect(bind).get_table_names())
    sequences = sa.table(
        "number_sequences",
        sa.column("key", sa.String()),
        sa.column("current_value", sa.Integer()),
        sa.column("updated_at", sa.DateTime()),
    )
    for key, table_name, column_name, pattern in seeds:
        if table_name not in tables:
            continue
        maximum = 0
        for value in bind.execute(sa.text(f"SELECT {column_name} FROM {table_name}")).scalars():
            match = re.match(pattern, str(value or ""))
            if match:
                maximum = max(maximum, int(match.group(1)))
        current = bind.execute(
            sa.select(sequences.c.current_value).where(sequences.c.key == key)
        ).scalar_one_or_none()
        if current is None:
            bind.execute(
                sequences.insert().values(key=key, current_value=maximum, updated_at=datetime.utcnow())
            )
        elif current < maximum:
            bind.execute(
                sequences.update().where(sequences.c.key == key).values(
                    current_value=maximum, updated_at=datetime.utcnow()
                )
            )


def downgrade() -> None:
    if "number_sequences" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("number_sequences")
