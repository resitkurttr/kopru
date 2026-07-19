# -*- coding: utf-8 -*-
"""
Köprü — FastAPI Gateway
 OpenAI uyumlu /v1/chat/completions + metadata tags (OmniRoute benzeri)
 Sağlık/istatistik API'leri + dashboard.
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .router import Router, Tier
from .config import load_config, load_catalog
from .mcp import handle_mcp_request
from .a2a import get_agent_card, handle_a2a_request

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def create_app(config_path: Optional[str] = None) -> FastAPI:
    app = FastAPI(title="Köprü Gateway", version="1.0.0")

    # CORS — GitHub Pages ve farklı origin'lerden erişim için
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    router = Router(config_path)

    class ChatMessage(BaseModel):
        role: str
        content: str

    class ChatRequest(BaseModel):
        model: str = ""
        messages: List[ChatMessage]
        max_tokens: int = 2048
        temperature: float = 0.7
        stream: bool = False
        metadata: Optional[Dict] = None  # OmniRoute benzeri: tags, tier

    @app.get("/")
    async def root():
        return {"service": "Köprü", "version": "1.0.0",
                "status": "running", "docs": "/docs"}

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

    @app.post("/v1/chat/completions")
    async def chat_completions(req: ChatRequest):
        """OpenAI uyumlu chat — auto-fallback + tag-based routing."""
        messages = [{"role": m.role, "content": m.content} for m in req.messages]

        # Metadata'dan tag/tier çöz (OmniRoute tagRouter benzeri)
        tier = None
        if req.metadata:
            tags = req.metadata.get("tags", [])
            if isinstance(tags, str):
                tags = tags.split(",")
            tier = router.resolve_tier(tags) if tags else None

        if req.stream:
            def gen():
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
            content = router.chat(
                messages, model=req.model, tier=tier,
                max_tokens=req.max_tokens, temperature=req.temperature,
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
                "usage": {"prompt_tokens": 0, "completion_tokens": 0,
                          "total_tokens": 0},
            })
        except Exception as e:
            return JSONResponse({"error": {"message": str(e), "type": "kopru_error"}},
                                status_code=502)

    @app.get("/api/status")
    async def status():
        return router.status()

    @app.get("/api/providers")
    async def providers():
        return router.health()

    @app.get("/api/providers-catalog")
    async def providers_catalog():
        """OmniRoute'tan alınan 277 provider kataloğu."""
        return load_catalog()

    @app.get("/dashboard")
    async def dashboard():
        """Basit HTML dashboard."""
        html_file = WEB_DIR / "static" / "dashboard.html"
        if html_file.exists():
            return HTMLResponse(html_file.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>Köprü Dashboard</h1><p>dashboard.html bulunamadı</p>")

    # ── MCP (Model Context Protocol) — OmniRoute /api/mcp benzeri ──

    @app.post("/api/mcp/stream")
    async def mcp_stream(request: Request):
        """MCP Streamable HTTP Transport (JSON-RPC 2.0)."""
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse({"jsonrpc": "2.0", "id": None,
                                  "error": {"code": -32700, "message": "Parse error"}},
                                 status_code=400)
        # Batch desteği
        if isinstance(payload, list):
            results = [handle_mcp_request(p, router) for p in payload]
            return JSONResponse(results)
        return JSONResponse(handle_mcp_request(payload, router))

    @app.get("/api/mcp/tools")
    async def mcp_tools():
        """MCP araç listesi (OmniRoute /api/mcp/tools benzeri)."""
        from .mcp import MCP_TOOLS
        return {"total": len(MCP_TOOLS), "tools": MCP_TOOLS}

    @app.get("/api/mcp/sse")
    async def mcp_sse():
        """MCP SSE transport (basit ping stream)."""
        def gen():
            import time
            while True:
                yield f"event: ping\ndata: {time.time()}\n\n"
                time.sleep(15)
        return StreamingResponse(gen(), media_type="text/event-stream")

    # ── A2A (Agent-to-Agent) — OmniRoute /.well-known/agent.json benzeri ──

    @app.get("/.well-known/agent.json")
    async def agent_card():
        """A2A Agent Card — başka ajanlar Köprü'yü keşfeder."""
        base = str(request.base_url).rstrip("/") if False else "http://localhost:20128"
        return JSONResponse(get_agent_card(base))

    @app.post("/a2a")
    async def a2a_endpoint(request: Request):
        """A2A JSON-RPC 2.0 endpoint."""
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse({"jsonrpc": "2.0", "id": None,
                                  "error": {"code": -32700, "message": "Parse error"}},
                                 status_code=400)
        return JSONResponse(handle_a2a_request(payload, router))

    return app


# Uvicorn için app referansı
app = create_app()
