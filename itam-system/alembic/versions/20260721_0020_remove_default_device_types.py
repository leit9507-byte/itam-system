"""remove default device type seed rows

Revision ID: 20260721_0020
Revises: 20260721_0019
Create Date: 2026-07-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260721_0020"
down_revision = "20260721_0019"
branch_labels = None
depends_on = None


DEFAULT_DEVICE_TYPES = [
    ("笔记本电脑", "移动办公电脑"),
    ("显示器", "显示设备"),
    ("网络设备", "交换机、路由器、防火墙等"),
    ("打印设备", "打印机和复合机"),
]


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "device_types" not in tables:
        return

    has_assets = "assets" in tables
    has_products = "product_catalogs" in tables
    for name, description in DEFAULT_DEVICE_TYPES:
        asset_filter = ""
        product_filter = ""
        if has_assets:
            asset_filter = "AND NOT EXISTS (SELECT 1 FROM assets WHERE assets.category = :name LIMIT 1)"
        if has_products:
            product_filter = "AND NOT EXISTS (SELECT 1 FROM product_catalogs WHERE product_catalogs.device_type = :name LIMIT 1)"
        bind.execute(
            sa.text(
                f"""
                DELETE FROM device_types
                WHERE name = :name
                  AND description = :description
                  {asset_filter}
                  {product_filter}
                """
            ),
            {"name": name, "description": description},
        )


def downgrade() -> None:
    pass
