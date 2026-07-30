import time
import logging
from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import asset, audit, company, dashboard, files, identity, inventory, lifecycle, location, notification, ops, product, purchase, repair, reporting, scan_binding, scrap, settings as settings_api, stocktake, supplier, todo
from app.core.database import Base, engine
from app.core.schema_compat import ensure_compatible_schema
from app.core.config import get_settings
from app.core.security import AuthMiddleware
from app.core.time import app_timezone
from app.services.sync_scheduler import start_daily_ldap_sync

logger = logging.getLogger("itam")


def init_database_with_retry(retries: int = 20, delay: float = 2.0) -> None:
    if get_settings().production_mode:
        return
    last_error = None
    for _ in range(retries):
        try:
            Base.metadata.create_all(bind=engine)
            ensure_compatible_schema(engine)
            return
        except OperationalError as exc:
            last_error = exc
            time.sleep(delay)
    if last_error:
        raise last_error


def validate_production_settings(settings) -> None:
    app_timezone()
    if not settings.production_mode:
        return
    if not settings.jwt_secret or len(settings.jwt_secret) < 32 or settings.jwt_secret.startswith("change-this"):
        raise RuntimeError("Production requires a long random JWT_SECRET")
    if not settings.cors_origins or "*" in settings.cors_origins:
        raise RuntimeError("Production requires explicit CORS_ORIGINS")
    if settings.database_url.startswith("sqlite"):
        raise RuntimeError("Production requires MySQL DATABASE_URL or DB_HOST/DB_NAME settings")
    if settings.db_pool_size < 1 or settings.db_max_overflow < 0:
        raise RuntimeError("Production database pool settings are invalid")


def validate_migration_state() -> None:
    settings = get_settings()
    if not settings.production_mode:
        return
    project_root = Path(__file__).resolve().parents[1]
    alembic_ini = project_root / "alembic.ini"
    if not alembic_ini.exists():
        raise RuntimeError("Production requires alembic.ini for migration state checks")
    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(project_root / "alembic"))
    config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
    script = ScriptDirectory.from_config(config)
    expected_heads = set(script.get_heads())
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current_heads = set(context.get_current_heads())
    if current_heads != expected_heads:
        raise RuntimeError(f"Database migration mismatch: current={sorted(current_heads) or ['<none>']} expected={sorted(expected_heads)}. Run alembic upgrade head before starting production.")


def create_app() -> FastAPI:
    init_database_with_retry()
    settings = get_settings()
    validate_production_settings(settings)
    validate_migration_state()

    app = FastAPI(
        title="Enterprise ITAM System",
        description="企业级 IT 资产全生命周期管理系统",
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuthMiddleware)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": "http_error"},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        return JSONResponse(
            status_code=422,
            content={"detail": "请求参数不正确，请检查后重试", "code": "validation_error", "errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request, exc):
        logger.exception("Unhandled request error: %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "服务器内部错误，请联系管理员", "code": "internal_error"},
        )

    app.include_router(asset.router)
    app.include_router(dashboard.router)
    app.include_router(company.router)
    app.include_router(purchase.router)
    app.include_router(repair.router)
    app.include_router(scrap.router)
    app.include_router(stocktake.router)
    app.include_router(lifecycle.router)
    app.include_router(location.router)
    app.include_router(supplier.router)
    app.include_router(product.router)
    app.include_router(inventory.router)
    app.include_router(identity.router)
    app.include_router(notification.router)
    app.include_router(settings_api.router)
    app.include_router(audit.router)
    app.include_router(files.router)
    app.include_router(reporting.router)
    app.include_router(scan_binding.router)
    app.include_router(ops.router)
    app.include_router(todo.router)

    @app.get("/")
    def health_check():
        return {"ok": True, "service": "itam-system"}

    @app.on_event("startup")
    async def start_background_jobs():
        app.state.ldap_sync_task = start_daily_ldap_sync()

    @app.on_event("shutdown")
    async def stop_background_jobs():
        task = getattr(app.state, "ldap_sync_task", None)
        if task:
            task.cancel()

    return app


app = create_app()
