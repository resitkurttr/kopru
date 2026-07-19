# -*- coding: utf-8 -*-
"""
Köprü — MCP (Model Context Protocol) Araçları
 OmniRoute benzeri: /api/mcp/stream + /api/mcp/sse + /api/mcp/tools
 Basit JSON-RPC 2.0 over HTTP/SSE.
"""
import json
import uuid
from typing import Dict, Any, List


# ── MCP Tools tanımı (OmniRoute /api/mcp/tools benzeri) ──────────────────

MCP_TOOLS: List[Dict] = [
    {
        "name": "kopru_chat",
        "description": "Köprü gateway üzerinden LLM sohbeti başlatır. "
                       "Tek endpoint, çoklu provider, otomatik fallback.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Kullanıcı mesajı"},
                "model": {"type": "string", "description": "Model (opsiyonel, boş=fallback)"},
            },
            "required": ["message"],
        },
    },
    {
        "name": "kopru_list_providers",
        "description": "Bağlı provider'ların sağlık durumunu döndürür.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "kopru_list_models",
        "description": "Mevcut tüm modelleri listeler.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "kopru_status",
        "description": "Gateway istatistiklerini döndürür (istek, fallback, token).",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def _call_tool(name: str, args: Dict, router) -> Any:
    """Aracı çalıştır (senkron)."""
    if name == "kopru_chat":
        msg = args.get("message", "")
        model = args.get("model", "")
        result = router.chat([{"role": "user", "content": msg}], model=model)
        return {"content": result}
    elif name == "kopru_list_providers":
        return {"providers": router.health()}
    elif name == "kopru_list_models":
        models = []
        for p in router.providers:
            for m in p.models:
                models.append({"id": m, "owned_by": p.name})
        return {"models": models}
    elif name == "kopru_status":
        return router.status()
    raise ValueError(f"Bilinmeyen araç: {name}")


def handle_mcp_request(payload: Dict, router) -> Dict:
    """
    JSON-RPC 2.0 handler.
    Desteklenen methodlar:
      - tools/list
      - tools/call
      - initialize
      - ping
    """
    method = payload.get("method", "")
    req_id = payload.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "Köprü", "version": "1.0.0"},
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "tools/list":
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {"tools": MCP_TOOLS},
        }

    if method == "tools/call":
        params = payload.get("params", {})
        name = params.get("name", "")
        args = params.get("arguments", {})
        try:
            result = _call_tool(name, args, router)
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                    "isError": False,
                },
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": str(e)}],
                    "isError": True,
                },
            }

    # Bilinmeyen method
    return {
        "jsonrpc": "2.0", "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }
