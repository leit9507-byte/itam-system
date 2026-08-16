from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field
from sqlalchemy.orm import Session

from app.core.time import TimezoneModel
from app.core.database import get_db
from app.core.security import operator_from_request
from app.models.user import IdentityProviderConfig
from app.services.asset_residual_service import AssetResidualService
from app.services.audit_log_service import AuditLogService
from app.services.feishu_jsapi_service import FeishuJsapiService


router = APIRouter(prefix="/settings", tags=["Settings"])


class CategoryResidualRate(TimezoneModel):
    category: str
    minimum_residual_rate: float = Field(ge=0, le=1)


class AssetResidualConfigPayload(TimezoneModel):
    method: str = Field(default="straight_line", pattern="^(straight_line|double_declining|sum_of_years_digits|fixed_rate)$")
    minimum_residual_rate: float = Field(ge=0, le=1)
    missing_basis_policy: str = "original"
    fixed_rate_value: float = Field(default=AssetResidualService.DEFAULT_FIXED_RATE_VALUE, ge=0, le=1)
    category_rates: list[CategoryResidualRate] = Field(default_factory=list)


class FeishuConfigPayload(TimezoneModel):
    enabled: bool = True
    app_id: str = ""
    app_secret: str = ""


def feishu_config_out(provider: IdentityProviderConfig | None) -> dict:
    config = (provider.config or {}) if provider else {}
    return {
        "id": provider.id if provider else None,
        "enabled": bool(provider.enabled) if provider else False,
        "app_id": config.get("app_id") or "",
        "app_secret_configured": bool(config.get("app_secret")),
        "last_test_status": provider.last_test_status if provider else None,
        "last_test_message": provider.last_test_message if provider else None,
        "updated_at": provider.updated_at if provider else None,
    }


def find_feishu_provider(db: Session) -> IdentityProviderConfig | None:
    return (
        db.query(IdentityProviderConfig)
        .filter(IdentityProviderConfig.provider_type == "feishu")
        .order_by(IdentityProviderConfig.id.asc())
        .first()
    )


@router.get("/asset-residual")
def get_asset_residual_config(db: Session = Depends(get_db)):
    return AssetResidualService.get_config(db)


@router.put("/asset-residual")
def save_asset_residual_config(payload: AssetResidualConfigPayload, request: Request, db: Session = Depends(get_db)):
    try:
        return AssetResidualService.save_config(db, payload.model_dump(), operator_from_request(request))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/feishu")
def get_feishu_config(db: Session = Depends(get_db)):
    return feishu_config_out(find_feishu_provider(db))


@router.put("/feishu")
def save_feishu_config(payload: FeishuConfigPayload, request: Request, db: Session = Depends(get_db)):
    provider = find_feishu_provider(db)
    existing_config = (provider.config or {}) if provider else {}
    app_id = payload.app_id.strip()
    app_secret = payload.app_secret.strip() or existing_config.get("app_secret") or ""
    if payload.enabled and not app_id:
        raise HTTPException(status_code=400, detail="启用飞书 JSAPI 前必须填写 App ID")
    if payload.enabled and not app_secret:
        raise HTTPException(status_code=400, detail="启用飞书 JSAPI 前必须填写 App Secret")
    if not provider:
        provider = IdentityProviderConfig(name="飞书扫码", provider_type="feishu")
        db.add(provider)
    provider.name = "飞书扫码"
    provider.provider_type = "feishu"
    provider.enabled = payload.enabled
    provider.config = {"app_id": app_id, "app_secret": app_secret}
    provider.last_test_status = None
    provider.last_test_message = None
    AuditLogService.record_operation(
        db,
        "settings",
        "save_feishu_config",
        operator_from_request(request),
        "feishu_config",
        str(provider.id or "new"),
        "保存飞书 JSAPI 配置",
        {"enabled": payload.enabled, "app_id": app_id, "app_secret_configured": bool(app_secret)},
    )
    db.commit()
    db.refresh(provider)
    FeishuJsapiService.clear_cache()
    return feishu_config_out(provider)


@router.post("/feishu/test")
def test_feishu_config(request: Request, db: Session = Depends(get_db)):
    provider = find_feishu_provider(db)
    if not provider or not provider.enabled:
        raise HTTPException(status_code=400, detail="请先保存并启用飞书配置")
    try:
        app_id, app_secret = FeishuJsapiService.find_credentials(db)
        FeishuJsapiService.clear_cache(app_id)
        FeishuJsapiService.get_cached_jsapi_ticket(app_id, app_secret)
        provider.last_test_status = "success"
        provider.last_test_message = "飞书凭证有效，JSAPI ticket 获取成功"
    except ValueError as exc:
        provider.last_test_status = "failed"
        provider.last_test_message = str(exc)[:255]
    AuditLogService.record_operation(
        db,
        "settings",
        "test_feishu_config",
        operator_from_request(request),
        "feishu_config",
        str(provider.id),
        "测试飞书 JSAPI 配置",
        {"result": provider.last_test_status},
    )
    db.commit()
    db.refresh(provider)
    return feishu_config_out(provider)
