from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import get_settings


settings = get_settings()


def engine_kwargs():
    options = {"pool_pre_ping": True, "echo": settings.db_echo}
    if settings.database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
        return options
    connect_args = {
        "connect_timeout": settings.db_connect_timeout,
        "charset": settings.db_charset,
    }
    if settings.db_timezone:
        connect_args["init_command"] = f"SET time_zone = '{settings.db_timezone}'"
    options.update(
        {
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "pool_recycle": settings.db_pool_recycle,
            "pool_timeout": settings.db_pool_timeout,
            "connect_args": connect_args,
        }
    )
    return options


engine = create_engine(settings.database_url, **engine_kwargs())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
