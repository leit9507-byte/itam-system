from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


PUBLIC_PATHS = {
    "/",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/auth/login",
}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or is_public_path(request.url.path):
            return await call_next(request)

        authorization = request.headers.get("authorization", "")
        if not is_valid_token(authorization):
            return JSONResponse({"detail": "Not authenticated"}, status_code=401)

        return await call_next(request)


def is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS or path.startswith("/auth/sso/")


def is_valid_token(authorization: str) -> bool:
    scheme, _, token = authorization.partition(" ")
    return scheme.lower() == "bearer" and token.startswith("mock-token-")
