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


def add_column(engine, columns: set[str], table: str, column: str, definition: str) -> None:
    if column in columns:
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
