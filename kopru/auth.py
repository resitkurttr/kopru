# -*- coding: utf-8 -*-
"""
Köprü — Auth Middleware
API key ile authentication + rate limiting.
"""
import time
from typing import Optional, Dict
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .database import verify_api_key, log_usage


# Rate limit state: {key_hash: [timestamps]}
_rate_cache: Dict[str, list] = {}


class AuthMiddleware(BaseHTTPMiddleware):
    """
    API key middleware.
    - /v1/*, /a2a → API key gerekli (chat proxy)
    - /api/keys, /api/providers, /api/status, /api/usage → serbest (dashboard)
    - /dashboard, /health, /, /docs → serbest
    """

    # Tamamen serbest yollar
    PUBLIC_PATHS = {
        "/", "/health", "/docs", "/openapi.json",
        "/dashboard", "/.well-known/agent.json",
        "/api/providers-catalog",
        "/v1/models",  # OpenAI uyumlu model listesi (discovery)
        "/api/mcp/tools",  # MCP araç listesi (discovery)
    }

    # Prefix ile serbest yollar (dashboard management)
    PUBLIC_PREFIXES = (
        "/api/keys",       # key CRUD
        "/api/providers",  # provider CRUD + toggle + health
        "/api/status",     # gateway stats
        "/api/usage",      # usage stats
    )

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Public path → auth yok
        if path in self.PUBLIC_PATHS or path.startswith("/dashboard"):
            return await call_next(request)

        # Public prefix → auth yok
        if any(path.startswith(p) for p in self.PUBLIC_PREFIXES):
            return await call_next(request)

        # API key al (header veya query)
        api_key = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:]
        if not api_key:
            api_key = request.query_params.get("api_key")

        # /v1/*, /a2a, /api/mcp/* → auth zorunlu
        if not api_key:
            return JSONResponse(
                {"error": {"message": "API key required. "
                           "Get one at /dashboard",
                           "type": "invalid_request_error"}},
                status_code=401
            )

        # Key doğrula
        key_info = verify_api_key(api_key)
        if not key_info:
            return JSONResponse(
                {"error": {"message": "Invalid or revoked API key",
                           "type": "invalid_request_error"}},
                status_code=401
            )

        # Rate limiting
        rate_limit = key_info.get("rate_limit", 60)
        key_hash = key_info["key_hash"]
        now = time.time()
        window = 60  # 1 dakika

        if key_hash not in _rate_cache:
            _rate_cache[key_hash] = []

        # Eski kayıtları temizle
        _rate_cache[key_hash] = [
            t for t in _rate_cache[key_hash] if now - t < window
        ]

        if len(_rate_cache[key_hash]) >= rate_limit:
            return JSONResponse(
                {"error": {"message": f"Rate limit exceeded ({rate_limit}/min)",
                           "type": "rate_limit_error"}},
                status_code=429,
                headers={"Retry-After": str(window)}
            )

        _rate_cache[key_hash].append(now)

        # Request state'e key bilgisi ekle
        request.state.api_key_info = key_info

        # Devam et
        start = time.time()
        response = await call_next(request)
        latency_ms = int((time.time() - start) * 1000)

        # Usage log (background'da, hata vermezse)
        try:
            log_usage(
                api_key_id=key_info["id"],
                provider_name="",
                model="",
                latency_ms=latency_ms,
                status_code=response.status_code,
            )
        except Exception:
            pass

        return response


def get_client_key(request: Request) -> Optional[Dict]:
    """Request'ten API key bilgisini al."""
    return getattr(request.state, "api_key_info", None)
