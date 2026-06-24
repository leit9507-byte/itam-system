import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from app.api import asset, audit, files, identity, product, purchase, repair, reporting, supplier
from app.core.database import Base, engine
from app.core.schema_compat import ensure_compatible_schema
from app.core.security import AuthMiddleware


def init_database_with_retry(retries: int = 20, delay: float = 2.0) -> None:
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


def create_app() -> FastAPI:
    init_database_with_retry()

    app = FastAPI(
        title="Enterprise ITAM System",
        description="企业级 IT 资产全生命周期管理系统",
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuthMiddleware)
    app.include_router(asset.router)
    app.include_router(purchase.router)
    app.include_router(repair.router)
    app.include_router(supplier.router)
    app.include_router(product.router)
    app.include_router(identity.router)
    app.include_router(audit.router)
    app.include_router(files.router)
    app.include_router(reporting.router)

    @app.get("/")
    def health_check():
        return {"ok": True, "service": "itam-system"}

    return app


app = create_app()
