from sqlalchemy import inspect, text


def ensure_compatible_schema(engine) -> None:
    inspector = inspect(engine)
    if "user_directory" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("user_directory")}
        add_column(engine, columns, "user_directory", "password_hash", "VARCHAR(255)")
        add_column(engine, columns, "user_directory", "failed_login_count", "INTEGER DEFAULT 0 NOT NULL")
        add_column(engine, columns, "user_directory", "locked_until", "DATETIME NULL")
        add_column(engine, columns, "user_directory", "last_login_at", "DATETIME NULL")
        add_column(engine, columns, "user_directory", "asset_assignment_required", "BOOLEAN DEFAULT 1 NOT NULL")

    if "purchases" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("purchases")}
        add_column(engine, columns, "purchases", "company", "VARCHAR(128) NULL")
        add_column(engine, columns, "purchases", "approval_no", "VARCHAR(128) NULL")
        add_column(engine, columns, "purchases", "supplier_name", "VARCHAR(128) NULL")
        add_column(engine, columns, "purchases", "purchase_reason", "TEXT NULL")
        add_column(engine, columns, "purchases", "created_at", "DATETIME NULL")
        with engine.begin() as conn:
            conn.execute(text(f"UPDATE purchases SET created_at = {current_timestamp_sql(engine)} WHERE created_at IS NULL"))

    if "purchase_items" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("purchase_items")}
        add_column(engine, columns, "purchase_items", "retirement_years", "INTEGER NULL")
        add_column(engine, columns, "purchase_items", "purchase_reason", "TEXT NULL")
        add_column(engine, columns, "purchase_items", "spec", "VARCHAR(255) NULL")

    if "product_catalogs" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("product_catalogs")}
        add_column(engine, columns, "product_catalogs", "retirement_years", "INTEGER NULL")

    if "assets" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("assets")}
        add_column(engine, columns, "assets", "asset_no", "VARCHAR(64) NULL")
        add_column(engine, columns, "assets", "company", "VARCHAR(128) NULL")
        add_column(engine, columns, "assets", "purchase_date", "DATETIME NULL")
        add_column(engine, columns, "assets", "purchase_approval_no", "VARCHAR(128) NULL")
        add_column(engine, columns, "assets", "purchase_supplier_name", "VARCHAR(128) NULL")
        add_column(engine, columns, "assets", "warranty_expire_date", "DATETIME NULL")
        add_column(engine, columns, "assets", "warranty_months", "INTEGER NULL")
        add_column(engine, columns, "assets", "remark", "TEXT NULL")
        with engine.begin() as conn:
            conn.execute(text("UPDATE assets SET company = '未设置公司' WHERE company IS NULL OR company = ''"))
            conn.execute(text("UPDATE assets SET status = 'scrapped' WHERE status = 'disposed'"))

    if "audit_rules" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("audit_rules")}
        add_column(engine, columns, "audit_rules", "scope_category", "VARCHAR(64) NULL")
        add_column(engine, columns, "audit_rules", "threshold_value", "FLOAT NULL")
        add_column(engine, columns, "audit_rules", "threshold_days", "INTEGER NULL")

    if "lifecycles" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("lifecycles")}
        add_column(engine, columns, "lifecycles", "remark", "TEXT NULL")

    if "notification_settings" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("notification_settings")}
        add_column(engine, columns, "notification_settings", "event_types", "JSON NULL")

    if "repair_records" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("repair_records")}
        add_column(engine, columns, "repair_records", "repair_type", "VARCHAR(64) DEFAULT '普通维修' NOT NULL")
        add_column(engine, columns, "repair_records", "repair_result", "VARCHAR(64) NULL")

    if "stocktake_items" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("stocktake_items")}
        add_column(engine, columns, "stocktake_items", "review_status", "VARCHAR(32) DEFAULT '无需复核' NOT NULL")
        add_column(engine, columns, "stocktake_items", "review_note", "TEXT NULL")
        add_column(engine, columns, "stocktake_items", "reviewed_by", "VARCHAR(128) NULL")
        add_column(engine, columns, "stocktake_items", "reviewed_at", "DATETIME NULL")
    if "scrap_requests" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("scrap_requests")}
        add_column(engine, columns, "scrap_requests", "retirement_flow_no", "VARCHAR(64) NULL")
        add_column(engine, columns, "scrap_requests", "retirement_date", "DATETIME NULL")
        add_column(engine, columns, "scrap_requests", "retirement_approval_no", "VARCHAR(128) NULL")
        add_column(engine, columns, "scrap_requests", "final_residual_value", "DECIMAL(12,2) DEFAULT 0")
        add_column(engine, columns, "scrap_requests", "disposal_remark", "TEXT NULL")
        add_column(engine, columns, "scrap_requests", "dispose_recipient_user_id", "VARCHAR(128) NULL")
        add_column(engine, columns, "scrap_requests", "dispose_recipient_name", "VARCHAR(128) NULL")
        add_column(engine, columns, "scrap_requests", "disposed_by", "VARCHAR(128) NULL")
        add_column(engine, columns, "scrap_requests", "disposed_at", "DATETIME NULL")
    if "asset_attachments" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("asset_attachments")}
        add_column(engine, columns, "asset_attachments", "status", "VARCHAR(32) DEFAULT 'active' NOT NULL")
        add_column(engine, columns, "asset_attachments", "archived_at", "DATETIME NULL")
        add_column(engine, columns, "asset_attachments", "deleted_at", "DATETIME NULL")
        add_column(engine, columns, "asset_attachments", "remark", "VARCHAR(512) NULL")

def add_column(engine, columns: set[str], table: str, column: str, definition: str) -> None:
    if column in columns:
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))


def current_timestamp_sql(engine) -> str:
    if engine.dialect.name == "sqlite":
        return "CURRENT_TIMESTAMP"
    return "NOW()"
