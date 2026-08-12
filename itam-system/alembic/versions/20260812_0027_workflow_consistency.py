"""enforce workflow consistency

Revision ID: 20260812_0027
Revises: 20260730_0026
Create Date: 2026-08-12
"""

from alembic import op
import sqlalchemy as sa


revision = "20260812_0027"
down_revision = "20260730_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "asset_checkouts" in tables:
        columns = {column["name"] for column in inspector.get_columns("asset_checkouts")}
        if "open_token" not in columns:
            op.add_column("asset_checkouts", sa.Column("open_token", sa.String(length=8), nullable=True))

        open_rows = bind.execute(
            sa.text(
                "SELECT id, asset_id FROM asset_checkouts "
                "WHERE status = 'open' ORDER BY asset_id, checked_out_at DESC, id DESC"
            )
        ).mappings().all()
        retained_assets: set[str] = set()
        for row in open_rows:
            if row["asset_id"] not in retained_assets:
                retained_assets.add(row["asset_id"])
                bind.execute(
                    sa.text("UPDATE asset_checkouts SET open_token = 'open' WHERE id = :id"),
                    {"id": row["id"]},
                )
                continue
            bind.execute(
                sa.text(
                    "UPDATE asset_checkouts SET status = 'closed', open_token = NULL, "
                    "checked_in_at = COALESCE(checked_in_at, CURRENT_TIMESTAMP), "
                    "checked_in_by = COALESCE(checked_in_by, 'migration') WHERE id = :id"
                ),
                {"id": row["id"]},
            )

        indexes = {index["name"] for index in sa.inspect(bind).get_indexes("asset_checkouts")}
        if "uq_asset_checkouts_single_open" not in indexes:
            op.create_index(
                "uq_asset_checkouts_single_open",
                "asset_checkouts",
                ["asset_id", "open_token"],
                unique=True,
            )

    if "user_directory" in tables:
        columns = {column["name"] for column in sa.inspect(bind).get_columns("user_directory")}
        if "ldap_missing_sync_count" not in columns:
            op.add_column(
                "user_directory",
                sa.Column("ldap_missing_sync_count", sa.Integer(), nullable=False, server_default="0"),
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "asset_checkouts" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("asset_checkouts")}
        if "uq_asset_checkouts_single_open" in indexes:
            op.drop_index("uq_asset_checkouts_single_open", table_name="asset_checkouts")
        columns = {column["name"] for column in sa.inspect(bind).get_columns("asset_checkouts")}
        if "open_token" in columns:
            op.drop_column("asset_checkouts", "open_token")
    if "user_directory" in tables:
        columns = {column["name"] for column in sa.inspect(bind).get_columns("user_directory")}
        if "ldap_missing_sync_count" in columns:
            op.drop_column("user_directory", "ldap_missing_sync_count")
