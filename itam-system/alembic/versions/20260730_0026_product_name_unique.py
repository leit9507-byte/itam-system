"""enforce unique product names

Revision ID: 20260730_0026
Revises: 20260729_0025
Create Date: 2026-07-30
"""

from alembic import op
import sqlalchemy as sa


revision = "20260730_0026"
down_revision = "20260729_0025"
branch_labels = None
depends_on = None


INDEX_NAME = "ix_product_catalogs_product_name"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "product_catalogs" not in inspector.get_table_names():
        return

    rows = bind.execute(
        sa.text(
            """
            SELECT id, product_name, device_type, brand, model, spec,
                   unit_price, default_warehouse, retirement_years
            FROM product_catalogs
            ORDER BY id
            """
        )
    ).mappings().all()
    canonical: dict[str, dict] = {}
    for row in rows:
        clean_name = str(row["product_name"] or "").strip()
        normalized = clean_name.lower()
        if not normalized:
            clean_name = f"未命名产品-{row['id']}"
            normalized = clean_name.lower()
        existing = canonical.get(normalized)
        if not existing:
            bind.execute(
                sa.text("UPDATE product_catalogs SET product_name = :name WHERE id = :id"),
                {"name": clean_name, "id": row["id"]},
            )
            canonical[normalized] = dict(row) | {"product_name": clean_name}
            continue

        merged = {}
        for field in ("device_type", "brand", "model", "spec", "unit_price", "default_warehouse", "retirement_years"):
            merged[field] = existing.get(field) or row.get(field)
        bind.execute(
            sa.text(
                """
                UPDATE product_catalogs
                SET device_type = :device_type,
                    brand = :brand,
                    model = :model,
                    spec = :spec,
                    unit_price = :unit_price,
                    default_warehouse = :default_warehouse,
                    retirement_years = :retirement_years
                WHERE id = :id
                """
            ),
            {**merged, "id": existing["id"]},
        )
        existing.update(merged)
        bind.execute(sa.text("DELETE FROM product_catalogs WHERE id = :id"), {"id": row["id"]})

    indexes = {item["name"]: item for item in sa.inspect(bind).get_indexes("product_catalogs")}
    current = indexes.get(INDEX_NAME)
    if current and not current.get("unique"):
        op.drop_index(INDEX_NAME, table_name="product_catalogs")
        current = None
    if not current:
        op.create_index(INDEX_NAME, "product_catalogs", ["product_name"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "product_catalogs" not in inspector.get_table_names():
        return
    indexes = {item["name"]: item for item in inspector.get_indexes("product_catalogs")}
    current = indexes.get(INDEX_NAME)
    if current and current.get("unique"):
        op.drop_index(INDEX_NAME, table_name="product_catalogs")
        op.create_index(INDEX_NAME, "product_catalogs", ["product_name"], unique=False)
