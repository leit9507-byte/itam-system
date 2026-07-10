from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote_plus
from urllib.parse import unquote_plus, urlparse

from sqlalchemy import create_engine, text

from app.core.config import database_config_path, get_settings, load_database_override


SECRET_MASK = "******"


def current_database_config() -> dict:
    saved = load_database_override() or {}
    settings = get_settings()
    source = "saved" if saved else "environment"
    env_config = parse_database_url(settings.database_url)
    source_config = saved or env_config
    return {
        "source": source,
        "enabled": bool(saved.get("enabled", False)),
        "driver": source_config.get("driver", "mysql"),
        "host": source_config.get("host", ""),
        "port": int(source_config.get("port") or 3306),
        "database": source_config.get("database", ""),
        "username": source_config.get("username", ""),
        "password": SECRET_MASK if source_config.get("password") else "",
        "charset": source_config.get("charset", settings.db_charset),
        "timezone": source_config.get("timezone", settings.db_timezone),
        "pool_size": int(source_config.get("pool_size") or settings.db_pool_size),
        "max_overflow": int(source_config.get("max_overflow") or settings.db_max_overflow),
        "pool_recycle": int(source_config.get("pool_recycle") or settings.db_pool_recycle),
        "pool_timeout": int(source_config.get("pool_timeout") or settings.db_pool_timeout),
        "connect_timeout": int(source_config.get("connect_timeout") or settings.db_connect_timeout),
        "runtime_url": mask_url(settings.database_url),
        "config_path": str(database_config_path()),
        "restart_required": False,
    }


def save_database_config(payload: dict) -> dict:
    password = payload.get("password")
    if password == SECRET_MASK:
        password = current_password()
    data = {
        "enabled": True,
        "driver": "mysql",
        "host": clean_string(payload.get("host")),
        "port": int(payload.get("port") or 3306),
        "database": clean_string(payload.get("database")),
        "username": clean_string(payload.get("username")),
        "password": password or "",
        "charset": clean_string(payload.get("charset")) or "utf8mb4",
        "timezone": clean_string(payload.get("timezone")) or "+08:00",
        "pool_size": int(payload.get("pool_size") or 10),
        "max_overflow": int(payload.get("max_overflow") or 20),
        "pool_recycle": int(payload.get("pool_recycle") or 1800),
        "pool_timeout": int(payload.get("pool_timeout") or 30),
        "connect_timeout": int(payload.get("connect_timeout") or 10),
    }
    validate_config(data)
    path = database_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    result = current_database_config()
    result.update({key: value for key, value in data.items() if key != "password"})
    result["password"] = SECRET_MASK if data.get("password") else ""
    result["source"] = "saved"
    result["restart_required"] = True
    return result


def test_database_config(payload: dict) -> dict:
    data = dict(payload)
    if data.get("password") == SECRET_MASK:
        data["password"] = current_password()
    validate_config(data)
    url = build_database_url_from_config(data)
    engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args(data))
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            version = scalar_or_empty(conn, "SELECT VERSION()")
            database = scalar_or_empty(conn, "SELECT DATABASE()")
        return {"ok": True, "message": "连接成功", "database": database, "version": version}
    except Exception as exc:
        return {"ok": False, "message": str(exc)}
    finally:
        engine.dispose()


def build_database_url_from_config(data: dict) -> str:
    host = clean_string(data.get("host"))
    port = int(data.get("port") or 3306)
    database = clean_string(data.get("database"))
    username = clean_string(data.get("username"))
    password = quote_plus(data.get("password") or "")
    charset = clean_string(data.get("charset")) or "utf8mb4"
    return f"mysql+pymysql://{quote_plus(username)}:{password}@{host}:{port}/{database}?charset={charset}"


def connect_args(data: dict) -> dict:
    args = {
        "connect_timeout": int(data.get("connect_timeout") or 10),
        "charset": clean_string(data.get("charset")) or "utf8mb4",
    }
    timezone = clean_string(data.get("timezone"))
    if timezone:
        args["init_command"] = f"SET time_zone = '{timezone}'"
    return args


def validate_config(data: dict) -> None:
    missing = [key for key in ["host", "database", "username"] if not clean_string(data.get(key))]
    if missing:
        raise ValueError("请填写数据库主机、库名和用户名")
    port = int(data.get("port") or 0)
    if port < 1 or port > 65535:
        raise ValueError("数据库端口不正确")


def scalar_or_empty(conn, statement: str) -> str:
    value = conn.execute(text(statement)).scalar()
    return str(value or "")


def load_raw_database_config() -> dict:
    path = database_config_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def current_password() -> str:
    saved = load_raw_database_config()
    if saved.get("password"):
        return saved["password"]
    return parse_database_url(get_settings().database_url).get("password", "")


def clean_string(value) -> str:
    return str(value or "").strip()


def mask_url(url: str) -> str:
    if "://" not in url or "@" not in url:
        return url
    scheme, rest = url.split("://", 1)
    credential, address = rest.split("@", 1)
    if ":" not in credential:
        return f"{scheme}://{credential}@{address}"
    user, _password = credential.split(":", 1)
    return f"{scheme}://{user}:{SECRET_MASK}@{address}"


def parse_database_url(url: str) -> dict:
    parsed = urlparse(url)
    if not parsed.scheme.startswith("mysql"):
        return {}
    query = dict(item.split("=", 1) for item in parsed.query.split("&") if "=" in item)
    return {
        "driver": "mysql",
        "host": parsed.hostname or "",
        "port": parsed.port or 3306,
        "database": parsed.path.lstrip("/"),
        "username": unquote_plus(parsed.username or ""),
        "password": unquote_plus(parsed.password or ""),
        "charset": query.get("charset", "utf8mb4"),
    }
