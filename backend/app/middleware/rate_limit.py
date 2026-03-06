import time
from collections import defaultdict

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

# Per-path rate limit configuration (requests per minute)
RATE_LIMITS: dict[str, int] = {
    "/api/auth/login": settings.rate_limit_login,
    "/api/auth/verify-email": settings.rate_limit_verify,
    "/api/auth/request-reset": settings.rate_limit_reset,
    "/api/auth/reset-password": settings.rate_limit_verify,
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        # Sliding window: {(path, ip): [timestamps]}
        self._requests: dict[tuple[str, str], list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        limit = RATE_LIMITS.get(path)

        if limit is not None and request.method == "POST":
            client_ip = request.client.host if request.client else "unknown"
            key = (path, client_ip)
            now = time.time()
            window_start = now - 60  # 1-minute sliding window

            # Clean old entries
            self._requests[key] = [t for t in self._requests[key] if t > window_start]

            if len(self._requests[key]) >= limit:
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many requests. Limit: {limit} per minute.",
                )

            self._requests[key].append(now)

        return await call_next(request)
