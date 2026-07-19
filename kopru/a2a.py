# -*- coding: utf-8 -*-
"""
Köprü — A2A (Agent-to-Agent) Agent Card
 OmniRoute benzeri: /.well-known/agent.json
 JSON-RPC 2.0 + SSE transport bildirimi.
"""
import json
from typing import Dict, Any


def get_agent_card(base_url: str = "http://localhost:20128") -> Dict[str, Any]:
    """A2A Agent Card — başka ajanların Köprü'yü keşfetmesi için."""
    return {
        "protocolVersion": "0.2.0",
        "name": "Köprü",
        "description": "Özgün AI Gateway — çoklu provider, tek endpoint, "
                       "otomatik fallback, token sıkıştırma. "
                       "OmniRoute benzeri mimari.",
        "url": f"{base_url}/.well-known/agent.json",
        "provider": {
            "organization": "resitkurttr",
            "url": "https://github.com/resitkurttr/kopru",
        },
        "capabilities": {
            "streaming": True,
            "pushNotifications": False,
            "stateTransitionHistory": False,
        },
        "skills": [
            {
                "id": "chat",
                "name": "AI Sohbet",
                "description": "Çoklu provider üzerinden LLM sohbeti (fallback zinciri).",
                "tags": ["ai", "llm", "chat", "gateway"],
                "examples": ["Merhaba, nasılsın?", "Python ile fibonacci yaz"],
            },
            {
                "id": "route",
                "name": "Akıllı Yönlendirme",
                "description": "Tag-based routing + circuit breaker ile model seçimi.",
                "tags": ["routing", "fallback", "load-balance"],
                "examples": ["code task", "simple question"],
            },
            {
                "id": "compress",
                "name": "Token Sıkıştırma",
                "description": "Bağlam penceresini sıkıştırarak token tasarrufu.",
                "tags": ["compression", "optimization"],
                "examples": ["long conversation summary"],
            },
        ],
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "transport": ["jsonrpc", "sse"],
        "endpoints": {
            "jsonrpc": f"{base_url}/a2a",
            "sse": f"{base_url}/a2a/sse",
            "mcp": f"{base_url}/api/mcp/stream",
        },
    }


def handle_a2a_request(payload: Dict, router) -> Dict:
    """A2A JSON-RPC 2.0 handler (basit)."""
    method = payload.get("method", "")
    req_id = payload.get("id")

    if method == "tasks/send" or method == "message/send":
        params = payload.get("params", {})
        msg = params.get("message", {})
        text = ""
        if isinstance(msg, dict):
            parts = msg.get("parts", [])
            for p in parts:
                if p.get("type") == "text":
                    text = p.get("text", "")
        try:
            result = router.chat([{"role": "user", "content": text}])
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "artifacts": [{
                        "parts": [{"type": "text", "text": result}],
                    }],
                },
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32000, "message": str(e)},
            }

    if method == "agent/ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    return {
        "jsonrpc": "2.0", "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }
