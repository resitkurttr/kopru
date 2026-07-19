# -*- coding: utf-8 -*-
"""
Köprü — Yapılandırma yönetimi
 YAML veya çevre değişkenlerinden provider ayarlarını yükler.
"""
import os
from pathlib import Path
from typing import Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


class ProviderConfig:
    """Tek bir AI sağlayıcı yapılandırması."""

    def __init__(self, name: str, base_url: str, api_key: str = "",
                 models: Optional[List[str]] = None, priority: int = 0,
                 enabled: bool = True):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.models = models or []
        self.priority = priority
        self.enabled = enabled

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "base_url": self.base_url,
            "api_key": self.api_key,
            "models": self.models,
            "priority": self.priority,
            "enabled": self.enabled,
        }


def load_config(path: Optional[str] = None) -> Dict:
    """
    config.yaml yükler. Bulunamazsa env'den varsayılan üretir.
    Dönüş: {"providers": [ProviderConfig, ...], "default_model": str}
    """
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH

    if cfg_path.exists() and yaml:
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        providers = []
        for p in data.get("providers", []):
            providers.append(ProviderConfig(
                name=p["name"],
                base_url=p["base_url"],
                api_key=p.get("api_key", ""),
                models=p.get("models", []),
                priority=p.get("priority", 0),
                enabled=p.get("enabled", True),
            ))
        # Env'den API key inject et (güvenlik: yaml'da plaintext yok)
        _inject_env_keys(providers)
        return {
            "providers": providers,
            "default_model": data.get("default_model", ""),
        }

    # Varsayılan: env tabanlı
    return _default_from_env()


def _inject_env_keys(providers: List[ProviderConfig]):
    """YAML'daki ${ENV_VAR} gösterimlerini gerçek değerle değiştir."""
    import re
    for p in providers:
        if p.api_key and p.api_key.startswith("${") and p.api_key.endswith("}"):
            env_name = p.api_key[2:-1]
            p.api_key = os.environ.get(env_name, "")


def _default_from_env() -> Dict:
    """Env değişkenlerinden basit config üret."""
    providers = []

    # OpenRouter
    if os.environ.get("OPENROUTER_API_KEY"):
        providers.append(ProviderConfig(
            name="openrouter", base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
            models=["deepseek/deepseek-chat", "google/gemma-4-31b-it:free"],
            priority=10,
        ))

    # OpenCode Zen
    if os.environ.get("OPENCODE_ZEN_API_KEY"):
        providers.append(ProviderConfig(
            name="opencode-zen", base_url="https://opencode.ai/zen/v1",
            api_key=os.environ["OPENCODE_ZEN_API_KEY"],
            models=["mimo-v2.5-free", "nemotron-3-ultra-free"],
            priority=20,
        ))

    # Ollama local
    ollama_base = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
    providers.append(ProviderConfig(
        name="ollama", base_url=f"{ollama_base}/v1",
        api_key="", models=["gemma4:31b-cloud"], priority=30,
    ))

    return {"providers": providers, "default_model": ""}


def resolve_model_chain(providers: List[ProviderConfig],
                         requested: str = "") -> List[tuple]:
    """
    İstenen modeli içeren provider'ı bulur, fallback zinciri üretir.
    Dönüş: [(base_url, api_key, model), ...] — sıralı
    """
    chain = []
    seen = set()
    enabled = [p for p in providers if p.enabled]
    enabled.sort(key=lambda x: x.priority)

    # 1. İstenen modeli belirli bir provider'da ara
    if requested:
        for p in enabled:
            if requested in p.models or requested == p.name:
                model = requested if requested in p.models else (p.models[0] if p.models else requested)
                key = (p.base_url, p.api_key, model)
                if key not in seen:
                    seen.add(key)
                    chain.append(key)

    # 2. Her provider'ın ilk modelini ekle (priority sırasıyla)
    for p in enabled:
        if not p.models:
            continue
        for m in p.models:
            key = (p.base_url, p.api_key, m)
            if key not in seen:
                seen.add(key)
                chain.append(key)

    return chain
