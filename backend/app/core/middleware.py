"""Request ids, per-request JSON log lines, and security headers."""
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.logging import log, request_id_var

_request_logger = logging.getLogger("aikyam.request")


def client_ip(request: Request) -> str:
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns/propagates X-Request-ID and writes one structured line per request."""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        token = request_id_var.set(rid)
        started = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            log(_request_logger, logging.ERROR, "request failed", method=request.method,
                path=request.url.path, ip=client_ip(request),
                duration_ms=round((time.perf_counter() - started) * 1000, 1))
            request_id_var.reset(token)
            raise
        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        response.headers["X-Request-ID"] = rid
        if request.url.path != "/api/health":  # health checks would drown the log
            level = logging.WARNING if response.status_code >= 500 else logging.INFO
            log(_request_logger, level, "request", method=request.method, path=request.url.path,
                status=response.status_code, duration_ms=duration_ms, ip=client_ip(request))
        request_id_var.reset(token)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Defensive headers on every response. The CSP is applied to HTML only
    (the SPA served from static_dir); API responses get the rest."""

    CSP = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.url.scheme == "https" or settings.trust_proxy_headers:
            headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if headers.get("content-type", "").startswith("text/html"):
            headers.setdefault("Content-Security-Policy", self.CSP)
        return response
