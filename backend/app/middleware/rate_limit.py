import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings

# Per-path rate limit configuration (requests per minute)
RATE_LIMITS: dict[str, int] = {
    "/api/auth/login": settings.rate_limit_login,
    "/api/auth/verify-email": settings.rate_limit_verify,
    "/api/auth/request-reset": settings.rate_limit_reset,
    "/api/auth/reset-password": settings.rate_limit_verify,
}


# Module-level storage so tests can call rate_limit_requests.clear()
rate_limit_requests: dict[tuple[str, str], list[float]] = defaultdict(list)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        limit = RATE_LIMITS.get(path)

        if limit is not None and request.method == "POST":
            client_ip = request.client.host if request.client else "unknown"
            key = (path, client_ip)
            now = time.time()
            window_start = now - 60  # 1-minute sliding window

            # Clean old entries
            rate_limit_requests[key] = [t for t in rate_limit_requests[key] if t > window_start]

            if len(rate_limit_requests[key]) >= limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": f"Too many requests. Limit: {limit} per minute."},
                )

            rate_limit_requests[key].append(now)

        return await call_next(request)
