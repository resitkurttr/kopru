# -*- coding: utf-8 -*-
"""
Köprü — Yapılandırma yönetimi
Dinamik provider CRUD (SQLite) + YAML fallback.
OmniRoute benzeri: provider ekleme/kaldırma, model senkronizasyonu.
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None

from .database import (
    list_providers as db_list_providers,
    create_provider as db_create_provider,
    update_provider as db_update_provider,
    delete_provider as db_delete_provider,
    get_provider_by_name,
)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
CATALOG_PATH = Path(__file__).resolve().parent / "providers_catalog.json"


class ProviderConfig:
    """Tek bir AI sağlayıcı yapılandırması."""

    def __init__(self, name: str, base_url: str, api_key: str = "",
                 models: Optional[List[str]] = None, priority: int = 0,
                 enabled: bool = True, category: str = "general",
                 provider_id: int = 0):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.models = models or []
        self.priority = priority
        self.enabled = enabled
        self.category = category
        self.id = provider_id

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "base_url": self.base_url,
            "api_key": self.api_key[:8] + "..." if self.api_key else "",
            "models": self.models,
            "priority": self.priority,
            "enabled": self.enabled,
            "category": self.category,
        }


def load_config(path: Optional[str] = None) -> Dict:
    """
    Config yükle.
    Öncelik: DB (dinamik) > YAML > env vars (fallback)
    """
    # 1. DB'den provider'ları yükle
    db_providers = _load_from_db()
    if db_providers:
        return {
            "providers": db_providers,
            "default_model": "",
        }

    # 2. YAML'dan yükle + DB'ye kaydet (ilk çalıştırmada)
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if cfg_path.exists() and yaml:
        providers = _load_from_yaml(cfg_path)
        # DB'ye migrate et
        for p in providers:
            existing = get_provider_by_name(p.name)
            if not existing:
                db_create_provider(
                    name=p.name, base_url=p.base_url,
                    api_key=p.api_key, models=p.models,
                    priority=p.priority,
                )
        return {"providers": providers, "default_model": ""}

    # 3. Env vars fallback
    providers = _default_from_env()
    for p in providers:
        existing = get_provider_by_name(p.name)
        if not existing:
            db_create_provider(
                name=p.name, base_url=p.base_url,
                api_key=p.api_key, models=p.models,
                priority=p.priority,
            )
    return {"providers": providers, "default_model": ""}


def _load_from_db() -> List[ProviderConfig]:
    """SQLite'dan provider'ları yükle."""
    rows = db_list_providers()
    providers = []
    for r in rows:
        providers.append(ProviderConfig(
            name=r["name"],
            base_url=r["base_url"],
            api_key=r.get("api_key", ""),
            models=r.get("models", []),
            priority=r.get("priority", 0),
            enabled=bool(r.get("enabled", 1)),
            category=r.get("category", "general"),
            provider_id=r.get("id", 0),
        ))
    return providers


def _load_from_yaml(cfg_path: Path) -> List[ProviderConfig]:
    """YAML'dan provider yükle."""
    with open(cfg_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    providers = []
    for p in data.get("providers", []):
        api_key = p.get("api_key", "")
        # Env inject
        if api_key.startswith("${") and api_key.endswith("}"):
            env_name = api_key[2:-1]
            api_key = os.environ.get(env_name, "")
        providers.append(ProviderConfig(
            name=p["name"],
            base_url=p["base_url"],
            api_key=api_key,
            models=p.get("models", []),
            priority=p.get("priority", 0),
            enabled=p.get("enabled", True),
            category=p.get("category", "general"),
        ))
    return providers


def _default_from_env() -> List[ProviderConfig]:
    """Env değişkenlerinden basit config üret."""
    providers = []

    if os.environ.get("OPENROUTER_API_KEY"):
        providers.append(ProviderConfig(
            name="openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
            models=["deepseek/deepseek-chat", "google/gemma-4-31b-it:free"],
            priority=10, category="cloud",
        ))

    if os.environ.get("OPENCODE_ZEN_API_KEY"):
        providers.append(ProviderConfig(
            name="opencode-zen",
            base_url="https://opencode.ai/zen/v1",
            api_key=os.environ["OPENCODE_ZEN_API_KEY"],
            models=["mimo-v2.5-free", "nemotron-3-ultra-free"],
            priority=20, category="cloud",
        ))

    ollama_base = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
    providers.append(ProviderConfig(
        name="ollama",
        base_url=f"{ollama_base}/v1",
        api_key="",
        models=["gemma4:31b-cloud"],
        priority=30, category="local",
    ))

    return providers


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
                model = requested if requested in p.models else (
                    p.models[0] if p.models else requested
                )
                key = (p.base_url, p.api_key, model)
                if key not in seen:
                    seen.add(key)
                    chain.append(key)

    # 2. Her provider'ın modellerini ekle (priority sırasıyla)
    for p in enabled:
        for m in p.models:
            key = (p.base_url, p.api_key, m)
            if key not in seen:
                seen.add(key)
                chain.append(key)

    return chain


def load_catalog() -> Dict:
    """Provider kataloğunu yükle — Python modülü tercih edilir, JSON fallback."""
    try:
        from .provider_catalog import PROVIDER_CATALOG, get_catalog_stats
        stats = get_catalog_stats()
        return {"providers": PROVIDER_CATALOG, "stats": stats}
    except ImportError:
        pass
    if CATALOG_PATH.exists():
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"providers": {}, "categories": {}}


# ── Dynamic Provider Management ───────────────────────────────────────────────

def add_provider(name: str, base_url: str, api_key: str = "",
                 models: List[str] = None, priority: int = 0,
                 category: str = "general") -> Dict:
    """Yeni provider ekle (UI'dan)."""
    return db_create_provider(
        name=name, base_url=base_url, api_key=api_key,
        models=models or [], priority=priority, category=category,
    )


def remove_provider(provider_id: int) -> bool:
    """Provider kaldır."""
    return db_delete_provider(provider_id)


def toggle_provider(provider_id: int, enabled: bool) -> bool:
    """Provider aç/kapat."""
    return db_update_provider(provider_id, enabled=enabled)


def update_provider_config(provider_id: int, **kwargs) -> bool:
    """Provider ayarlarını güncelle."""
    return db_update_provider(provider_id, **kwargs)
