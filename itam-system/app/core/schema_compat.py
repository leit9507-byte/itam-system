from sqlalchemy import inspect, text


def ensure_compatible_schema(engine) -> None:
    inspector = inspect(engine)
    if "user_directory" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("user_directory")}
        add_column(engine, columns, "user_directory", "password_hash", "VARCHAR(255)")
        add_column(engine, columns, "user_directory", "failed_login_count", "INTEGER DEFAULT 0 NOT NULL")
        add_column(engine, columns, "user_directory", "locked_until", "DATETIME NULL")
        add_column(engine, columns, "user_directory", "last_login_at", "DATETIME NULL")

    if "purchases" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("purchases")}
        add_column(engine, columns, "purchases", "supplier_name", "VARCHAR(128) NULL")

    if "purchase_items" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("purchase_items")}
        add_column(engine, columns, "purchase_items", "retirement_years", "INTEGER NULL")

    if "product_catalogs" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("product_catalogs")}
        add_column(engine, columns, "product_catalogs", "retirement_years", "INTEGER NULL")

    if "assets" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("assets")}
        add_column(engine, columns, "assets", "company", "VARCHAR(128) NULL")
        add_column(engine, columns, "assets", "purchase_date", "DATETIME NULL")
        add_column(engine, columns, "assets", "purchase_approval_no", "VARCHAR(128) NULL")
        add_column(engine, columns, "assets", "purchase_supplier_name", "VARCHAR(128) NULL")
        add_column(engine, columns, "assets", "warranty_expire_date", "DATETIME NULL")
        add_column(engine, columns, "assets", "warranty_months", "INTEGER NULL")
        with engine.begin() as conn:
            conn.execute(text("UPDATE assets SET company = '未设置公司' WHERE company IS NULL OR company = ''"))

    if "audit_rules" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("audit_rules")}
        add_column(engine, columns, "audit_rules", "scope_category", "VARCHAR(64) NULL")
        add_column(engine, columns, "audit_rules", "threshold_value", "FLOAT NULL")
        add_column(engine, columns, "audit_rules", "threshold_days", "INTEGER NULL")

    if "lifecycles" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("lifecycles")}
        add_column(engine, columns, "lifecycles", "remark", "TEXT NULL")


def add_column(engine, columns: set[str], table: str, column: str, definition: str) -> None:
    if column in columns:
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
