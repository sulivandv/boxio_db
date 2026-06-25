from __future__ import annotations

import time
from collections import defaultdict, deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limit simples por IP para endpoints de licença.

    Esta proteção substitui o rate limit que antes seria feito no Nginx.
    Para Fase 1 em Render, um controle em memória é suficiente para reduzir
    abuso básico. Em produção maior, use um rate limit distribuído ou WAF.
    """

    def __init__(self, app, requests_per_minute: int = 60) -> None:
        super().__init__(app)
        self.requests_per_minute = max(1, int(requests_per_minute or 60))
        self.window_seconds = 60
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._protected_prefixes = (
            "/licenses/",
            "/api/license/",
            "/admin/",
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path or "/"
        if not path.startswith(self._protected_prefixes):
            return await call_next(request)

        client_ip = self._client_ip(request)
        now = time.monotonic()
        bucket = self._hits[client_ip]

        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()

        if len(bucket) >= self.requests_per_minute:
            return JSONResponse(
                status_code=429,
                content={
                    "ok": False,
                    "status": "rate_limited",
                    "message": "Muitas requisições em pouco tempo. Tente novamente em instantes.",
                },
            )

        bucket.append(now)
        return await call_next(request)

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
