"""track the LDAP provider that owns each directory user

Revision ID: 20260717_0016
Revises: 20260717_0015
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa


revision = "20260717_0016"
down_revision = "20260717_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("user_directory")}
    if "identity_provider_id" not in columns:
        op.add_column("user_directory", sa.Column("identity_provider_id", sa.Integer(), nullable=True))

    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("user_directory")}
    if "ix_user_directory_identity_provider_id" not in indexes:
        op.create_index("ix_user_directory_identity_provider_id", "user_directory", ["identity_provider_id"])

    foreign_keys = {foreign_key.get("name") for foreign_key in inspector.get_foreign_keys("user_directory")}
    if "fk_user_directory_identity_provider" not in foreign_keys:
        op.create_foreign_key(
            "fk_user_directory_identity_provider",
            "user_directory",
            "identity_provider_configs",
            ["identity_provider_id"],
            ["id"],
            ondelete="SET NULL",
        )

    providers = sa.table(
        "identity_provider_configs",
        sa.column("id", sa.Integer()),
        sa.column("provider_type", sa.String()),
    )
    users = sa.table(
        "user_directory",
        sa.column("source", sa.String()),
        sa.column("identity_provider_id", sa.Integer()),
    )
    ldap_provider_ids = list(bind.execute(sa.select(providers.c.id).where(providers.c.provider_type == "ldap")).scalars())
    if len(ldap_provider_ids) == 1:
        bind.execute(
            users.update()
            .where(users.c.source == "ldap", users.c.identity_provider_id.is_(None))
            .values(identity_provider_id=ldap_provider_ids[0])
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("user_directory")}
    if "identity_provider_id" in columns:
        foreign_keys = {foreign_key.get("name") for foreign_key in inspector.get_foreign_keys("user_directory")}
        if "fk_user_directory_identity_provider" in foreign_keys:
            op.drop_constraint("fk_user_directory_identity_provider", "user_directory", type_="foreignkey")
        indexes = {index["name"] for index in inspector.get_indexes("user_directory")}
        if "ix_user_directory_identity_provider_id" in indexes:
            op.drop_index("ix_user_directory_identity_provider_id", table_name="user_directory")
        op.drop_column("user_directory", "identity_provider_id")
