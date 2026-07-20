# -*- coding: utf-8 -*-
"""
Köprü — FastAPI Gateway (OmniRoute benzeri)
OpenAI uyumlu /v1/chat/completions + provider management + API key sistemi.
"""
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .router import Router, Tier
from .config import (
    load_config, load_catalog, add_provider, remove_provider,
    toggle_provider, update_provider_config,
)
from .mcp import handle_mcp_request
from .a2a import get_agent_card, handle_a2a_request
from .auth import AuthMiddleware
from .database import (
    create_api_key, list_api_keys, revoke_api_key, delete_api_key,
    get_usage_stats, list_providers as db_list_providers,
    init_db,
)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
ROOT_DIR = Path(__file__).resolve().parent.parent


def create_app(config_path: Optional[str] = None) -> FastAPI:
    app = FastAPI(title="Köprü Gateway", version="2.0.0",
                  description="Özgün AI Gateway — OmniRoute benzeri")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Auth middleware
    app.add_middleware(AuthMiddleware)

    # Router init
    router = Router(config_path)

    # ── Pydantic Models ───────────────────────────────────────────────────

    class ChatMessage(BaseModel):
        role: str
        content: str

    class ChatRequest(BaseModel):
        model: str = ""
        messages: List[ChatMessage]
        max_tokens: int = 2048
        temperature: float = 0.7
        stream: bool = False
        metadata: Optional[Dict] = None

    class ProviderCreate(BaseModel):
        name: str
        base_url: str
        api_key: str = ""
        models: List[str] = []
        priority: int = 0
        category: str = "general"

    class ProviderUpdate(BaseModel):
        name: Optional[str] = None
        base_url: Optional[str] = None
        api_key: Optional[str] = None
        models: Optional[List[str]] = None
        priority: Optional[int] = None
        enabled: Optional[bool] = None
        category: Optional[str] = None

    class APIKeyCreate(BaseModel):
        name: str = ""
        user_id: str = ""
        rate_limit: int = 60

    # ── Public Endpoints ──────────────────────────────────────────────────

    @app.get("/")
    async def root():
        return RedirectResponse(url="/dashboard")

    @app.get("/health")
    async def health():
        return {"status": "ok", "providers": router.health()}

    @app.get("/v1/models")
    async def list_models():
        """OpenAI uyumlu model listesi."""
        models = []
        for p in router.providers:
            for m in p.models:
                models.append({
                    "id": m,
                    "object": "model",
                    "owned_by": p.name,
                })
        return {"object": "list", "data": models}

    # ── Chat (auth middleware ile korunuyor) ──────────────────────────────

    @app.post("/v1/chat/completions")
    async def chat_completions(req: ChatRequest, request: Request):
        """OpenAI uyumlu chat — auto-fallback + tag-based routing."""
        messages = [{"role": m.role, "content": m.content} for m in req.messages]

        # Metadata'dan tag/tier çöz
        tier = None
        if req.metadata:
            tags = req.metadata.get("tags", [])
            if isinstance(tags, str):
                tags = tags.split(",")
            tier = router.resolve_tier(tags) if tags else None

        # API key bilgisi (middleware'den)
        key_info = getattr(request.state, "api_key_info", None)

        if req.stream:
            def gen():
                start = time.time()
                for token in router.chat_stream(
                    messages, model=req.model, tier=tier,
                    max_tokens=req.max_tokens, temperature=req.temperature,
                ):
                    chunk = {
                        "choices": [{"delta": {"content": token},
                                     "index": 0, "finish_reason": None}],
                        "object": "chat.completion.chunk",
                    }
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(gen(), media_type="text/event-stream")

        try:
            start = time.time()
            content = router.chat(
                messages, model=req.model, tier=tier,
                max_tokens=req.max_tokens, temperature=req.temperature,
            )
            latency_ms = int((time.time() - start) * 1000)

            # Usage log
            from .database import log_usage
            log_usage(
                api_key_id=key_info["id"] if key_info else None,
                provider_name=router.stats.last_provider or "",
                model=req.model or router.default_model or "auto",
                latency_ms=latency_ms,
                status_code=200,
            )

            return JSONResponse({
                "id": "kopru-" + os.urandom(4).hex(),
                "object": "chat.completion",
                "model": req.model or router.default_model or "kopru",
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": router.stats.total_tokens,
                },
            })
        except Exception as e:
            from .database import log_usage
            log_usage(
                api_key_id=key_info["id"] if key_info else None,
                provider_name="",
                model=req.model or "",
                status_code=502,
                error=str(e)[:200],
            )
            return JSONResponse(
                {"error": {"message": str(e), "type": "kopru_error"}},
                status_code=502,
            )

    # ── Provider Management (Dashboard) ───────────────────────────────────

    @app.get("/api/providers")
    async def providers():
        """Provider listesi (detaylı)."""
        return {"providers": [p.to_dict() for p in router.providers]}

    @app.post("/api/providers")
    async def create_provider_endpoint(provider: ProviderCreate):
        """Yeni provider ekle."""
        result = add_provider(
            name=provider.name,
            base_url=provider.base_url,
            api_key=provider.api_key,
            models=provider.models,
            priority=provider.priority,
            category=provider.category,
        )
        # Router'ı yeniden yükle
        router._reload_config()
        return {"status": "created", "provider": result}

    @app.put("/api/providers/{provider_id}")
    async def update_provider_endpoint(provider_id: int,
                                       update: ProviderUpdate):
        """Provider güncelle."""
        kwargs = {k: v for k, v in update.dict().items() if v is not None}
        success = update_provider_config(provider_id, **kwargs)
        if success:
            router._reload_config()
            return {"status": "updated"}
        raise HTTPException(404, "Provider not found")

    @app.delete("/api/providers/{provider_id}")
    async def delete_provider_endpoint(provider_id: int):
        """Provider sil."""
        success = remove_provider(provider_id)
        if success:
            router._reload_config()
            return {"status": "deleted"}
        raise HTTPException(404, "Provider not found")

    @app.post("/api/providers/{provider_id}/toggle")
    async def toggle_provider_endpoint(provider_id: int,
                                       enabled: bool = True):
        """Provider aç/kapat."""
        success = toggle_provider(provider_id, enabled)
        if success:
            router._reload_config()
            return {"status": "toggled", "enabled": enabled}
        raise HTTPException(404, "Provider not found")

    @app.get("/api/providers/{provider_id}/health")
    async def provider_health_detail(provider_id: int):
        """Provider sağlık detayı."""
        for p in router.providers:
            if p.id == provider_id:
                br = router._breaker(p.base_url)
                return {
                    "name": p.name,
                    "healthy": not br.should_skip(),
                    "failures": br.failures,
                    "circuit_open": br.open,
                    "cooldown_remaining": max(0, br.cooldown - (
                        time.time() - br.last_failure
                    )) if br.open else 0,
                }
        raise HTTPException(404, "Provider not found")

    # ── API Key Management ────────────────────────────────────────────────

    @app.get("/api/keys")
    async def list_keys():
        """Tüm API key'leri listele."""
        return {"keys": list_api_keys()}

    @app.post("/api/keys")
    async def create_key(req: APIKeyCreate):
        """Yeni API key üret."""
        result = create_api_key(
            name=req.name, user_id=req.user_id, rate_limit=req.rate_limit
        )
        return {"status": "created", "key": result}

    @app.post("/api/keys/{key_id}/revoke")
    async def revoke_key(key_id: int):
        """API key'i devre dışı bırak."""
        success = revoke_api_key(key_id)
        if success:
            return {"status": "revoked"}
        raise HTTPException(404, "Key not found")

    @app.delete("/api/keys/{key_id}")
    async def delete_key(key_id: int):
        """API key'i sil."""
        success = delete_api_key(key_id)
        if success:
            return {"status": "deleted"}
        raise HTTPException(404, "Key not found")

    # ── Usage & Stats ─────────────────────────────────────────────────────

    @app.get("/api/status")
    async def status():
        """Gateway istatistikleri."""
        stats = router.status()
        usage = get_usage_stats(days=7)
        return {**stats, "usage_7d": usage}

    @app.get("/api/usage")
    async def usage(days: int = 7):
        """Kullanım istatistikleri."""
        return get_usage_stats(days=days)

    @app.get("/api/providers-catalog")
    async def providers_catalog():
        """OmniRoute'tan alınan provider kataloğu."""
        return load_catalog()

    # ── Dashboard ─────────────────────────────────────────────────────────

    @app.get("/dashboard")
    async def dashboard():
        """Köprü — Provider management + API key + usage dashboard."""
        # Tercih: root index.html (büyük dashboard), fallback: web/static/dashboard.html
        for candidate in [ROOT_DIR / "index.html", WEB_DIR / "static" / "dashboard.html"]:
            if candidate.exists():
                return HTMLResponse(candidate.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>Köprü Dashboard</h1><p>Yükleniyor...</p>")

    # ── MCP (Model Context Protocol) ─────────────────────────────────────

    @app.post("/api/mcp/stream")
    async def mcp_stream(request: Request):
        """MCP Streamable HTTP Transport (JSON-RPC 2.0)."""
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(
                {"jsonrpc": "2.0", "id": None,
                 "error": {"code": -32700, "message": "Parse error"}},
                status_code=400,
            )
        if isinstance(payload, list):
            results = [handle_mcp_request(p, router) for p in payload]
            return JSONResponse(results)
        return JSONResponse(handle_mcp_request(payload, router))

    @app.get("/api/mcp/tools")
    async def mcp_tools():
        """MCP araç listesi."""
        from .mcp import MCP_TOOLS
        return {"total": len(MCP_TOOLS), "tools": MCP_TOOLS}

    @app.get("/api/mcp/sse")
    async def mcp_sse():
        """MCP SSE transport."""
        def gen():
            while True:
                yield f"event: ping\ndata: {time.time()}\n\n"
                time.sleep(15)
        return StreamingResponse(gen(), media_type="text/event-stream")

    # ── A2A (Agent-to-Agent) ─────────────────────────────────────────────

    @app.get("/.well-known/agent.json")
    async def agent_card():
        """A2A Agent Card."""
        base = "http://localhost:20128"
        return JSONResponse(get_agent_card(base))

    @app.post("/a2a")
    async def a2a_endpoint(request: Request):
        """A2A JSON-RPC 2.0 endpoint."""
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse(
                {"jsonrpc": "2.0", "id": None,
                 "error": {"code": -32700, "message": "Parse error"}},
                status_code=400,
            )
        return JSONResponse(handle_a2a_request(payload, router))

    return app


# Uvicorn için app referansı
app = create_app()
