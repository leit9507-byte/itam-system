from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.auth import decode_access_token
from app.core.database import SessionLocal
from app.models.user import RolePermission, UserDirectory


PUBLIC_PATHS = {
    "/",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/auth/login",
    "/auth/me/permissions",
    "/approval/feishu/callback",
}

RESOURCE_PREFIXES = {
    "/asset": "asset",
    "/company": "asset",
    "/location": "asset",
    "/inventory": "asset",
    "/purchase": "purchase",
    "/repair": "repair",
    "/scrap": "asset",
    "/stocktake": "asset",
    "/lifecycle": "asset",
    "/supplier": "supplier",
    "/catalog": "catalog",
    "/audit": "audit",
    "/users": "identity",
    "/identity": "identity",
    "/notification": "identity",
    "/rbac": "rbac",
    "/files": "file",
    "/reports": "report",
    "/todo": "asset",
    "/approval": "rbac",
    "/ops": "ops",
}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or is_public_path(request.url.path):
            return await call_next(request)

        authorization = request.headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer":
            return JSONResponse({"detail": "Not authenticated"}, status_code=401)

        payload = decode_access_token(token)
        if not payload:
            return JSONResponse({"detail": "Invalid or expired token"}, status_code=401)

        with SessionLocal() as db:
            user = db.get(UserDirectory, payload["sub"])
            if not user or user.status != "active":
                return JSONResponse({"detail": "User disabled or not found"}, status_code=403)
            if not has_permission(db, user.role, request.url.path, method_to_action(request.method)):
                return JSONResponse({"detail": "Permission denied"}, status_code=403)
            request.state.user = {
                "user_id": user.user_id,
                "username": user.username,
                "display_name": user.display_name,
                "role": user.role,
                "dept_id": user.dept_id,
                "dept_name": user.dept_name,
            }

        return await call_next(request)


def is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS or path.startswith("/auth/sso/") or path.startswith("/auth/callback/")


def method_to_action(method: str) -> str:
    return {"GET": "read", "POST": "write", "PUT": "write", "PATCH": "write", "DELETE": "delete"}.get(method.upper(), "read")


def resource_for_path(path: str) -> str:
    for prefix, resource in RESOURCE_PREFIXES.items():
        if path.startswith(prefix):
            return resource
    return "system"


def has_permission(db, role: str, path: str, action: str) -> bool:
    if role == "admin":
        return True
    resource = resource_for_path(path)
    permission = (
        db.query(RolePermission)
        .filter(
            RolePermission.role == role,
            RolePermission.resource == resource,
            RolePermission.action.in_([action, "*"]),
            RolePermission.allowed.is_(True),
        )
        .first()
    )
    return bool(permission)


def operator_from_request(request: Request) -> str:
    user = getattr(request.state, "user", {}) or {}
    name = user.get("display_name") or user.get("username") or user.get("user_id") or "system"
    role = user.get("role")
    label = f"{name}({role})" if role else name
    return label[:64]


def user_context_from_request(request: Request) -> dict:
    return getattr(request.state, "user", {}) or {}


def can_view_all_data(user_context: dict | None) -> bool:
    role = ((user_context or {}).get("role") or "").lower()
    return role in {"admin", "auditor"}


def is_department_manager(user_context: dict | None) -> bool:
    role = ((user_context or {}).get("role") or "").lower()
    return role in {"dept_manager", "department_manager", "manager", "部门管理员"}


def scoped_dept_id(user_context: dict | None) -> str | None:
    user_context = user_context or {}
    return user_context.get("dept_id") or user_context.get("dept_name")


def scoped_user_identities(user_context: dict | None) -> list[str]:
    user_context = user_context or {}
    return [value for value in [user_context.get("user_id"), user_context.get("username")] if value]
