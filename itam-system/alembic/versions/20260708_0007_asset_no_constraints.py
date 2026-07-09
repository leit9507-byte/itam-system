"""enforce asset number and serial number quality

Revision ID: 20260708_0007
Revises: 20260708_0006
Create Date: 2026-07-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_0007"
down_revision = "20260708_0006"
branch_labels = None
depends_on = None


def has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def clean_asset_no(value: str | None) -> str:
    clean = (value or "").strip()
    if not clean:
        return ""
    if clean == "0" or (clean.isdigit() and int(clean) == 0):
        return ""
    return clean


def unique_candidate(asset_id: str, asset_no: str | None, used: set[str]) -> str:
    candidate = clean_asset_no(asset_no) or asset_id
    if candidate not in used:
        used.add(candidate)
        return candidate
    base = asset_id[:54]
    index = 1
    while True:
        candidate = f"{base}-{index}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        index += 1


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT asset_id, asset_no FROM assets ORDER BY asset_id")).mappings().all()
    used: set[str] = set()
    for row in rows:
        asset_id = str(row["asset_id"])
        next_asset_no = unique_candidate(asset_id, row.get("asset_no"), used)
        if next_asset_no != row.get("asset_no"):
            bind.execute(
                sa.text("UPDATE assets SET asset_no = :asset_no WHERE asset_id = :asset_id"),
                {"asset_no": next_asset_no, "asset_id": asset_id},
            )

    bind.execute(sa.text("UPDATE assets SET sn = NULL WHERE sn IS NOT NULL AND TRIM(sn) = ''"))
    dialect = bind.dialect.name
    if dialect in {"mysql", "mariadb", "postgresql"}:
        op.alter_column("assets", "asset_no", existing_type=sa.String(length=64), nullable=False)
    if not has_index("assets", "ux_assets_asset_no"):
        op.create_index("ux_assets_asset_no", "assets", ["asset_no"], unique=True)


def downgrade() -> None:
    if has_index("assets", "ux_assets_asset_no"):
        op.drop_index("ux_assets_asset_no", table_name="assets")
    bind = op.get_bind()
    if bind.dialect.name in {"mysql", "mariadb", "postgresql"}:
        op.alter_column("assets", "asset_no", existing_type=sa.String(length=64), nullable=True)
