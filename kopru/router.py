# -*- coding: utf-8 -*-
"""
Köprü — Akıllı Yönlendirici (Router)
 OmniRoute benzeri mimari:
  - Fallback zinciri (priority sıralı, exclude destekli)
  - Circuit breaker (sağlık kontrolü, cooldown)
  - Tag-based routing (görev türüne göre model seçimi)
"""
import time
import json
import threading
from typing import Dict, List, Optional, Generator, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

import requests

from .config import ProviderConfig, load_config, resolve_model_chain
from .compression import Compressor, count_tokens_approx


class Tier(str, Enum):
    """Fitness tier — OmniRoute pipeline.ts ile aynı mantık."""
    BEST_REASONING = "best-reasoning"
    CHEAPEST = "cheapest"
    MODERATE = "moderate"


@dataclass
class CircuitState:
    """Circuit breaker durumu (OmniRoute degradation.ts esinli)."""
    failures: int = 0
    last_failure: float = 0.0
    cooldown: float = 60.0  # saniye
    open: bool = False

    def should_skip(self) -> bool:
        if not self.open:
            return False
        # Cooldown doldu mu?
        if time.time() - self.last_failure > self.cooldown:
            self.open = False
            self.failures = 0
            return False
        return True

    def record_failure(self):
        self.failures += 1
        self.last_failure = time.time()
        if self.failures >= 3:
            self.open = True

    def record_success(self):
        self.failures = 0
        self.open = False


@dataclass
class RouteStats:
    """Yönlendirme istatistikleri."""
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    fallback_used: int = 0
    total_tokens: int = 0
    total_tokens_saved: int = 0
    per_provider: Dict[str, int] = field(default_factory=dict)
    last_error: str = ""


class Router:
    """OpenAI uyumlu çoklu-provider router (OmniRoute benzeri)."""

    def __init__(self, config_path: Optional[str] = None):
        self.config = load_config(config_path)
        self.providers: List[ProviderConfig] = self.config["providers"]
        self.default_model = self.config["default_model"]
        self.stats = RouteStats()
        # Circuit breaker: base_url -> CircuitState
        self._breakers: Dict[str, CircuitState] = {}
        self._lock = threading.Lock()
        # Compression (OmniRoute RTK/Caveman esinli)
        self.compressor = Compressor(strategy="simple", threshold=10, keep_recent=4)

    # ── Circuit breaker helpers ──────────────────────────────────────────

    def _breaker(self, base_url: str) -> CircuitState:
        with self._lock:
            if base_url not in self._breakers:
                self._breakers[base_url] = CircuitState()
            return self._breakers[base_url]

    # ── Header / error classification ────────────────────────────────────

    def _headers(self, api_key: str, base_url: str) -> Dict:
        h = {
            "Authorization": f"Bearer {api_key}" if api_key else "",
            "Content-Type": "application/json",
            "User-Agent": "Kopru/1.0 (Alpai Gateway)",
        }
        if "openrouter.ai" in base_url:
            h["HTTP-Referer"] = "https://kopru.local"
            h["X-Title"] = "Kopru"
        return h

    def _classify(self, status: int) -> str:
        if status == 429:
            return "rate_limit"
        if status == 402:
            return "quota"
        if status == 401:
            return "auth"
        if status == 503:
            return "unavailable"
        if status >= 500:
            return "server"
        return f"http_{status}"

    # ── Core chat (sync) ─────────────────────────────────────────────────

    def chat(self, messages: List[Dict], model: str = "",
             tier: Optional[Tier] = None, **kwargs) -> str:
        """Senkron sohbet — auto-fallback + circuit breaker + compression."""
        # Compression uygula (token tasarrufu)
        original_tokens = count_tokens_approx(messages)
        messages = self.compressor.compress(messages, summarizer=kwargs.get("summarizer"))
        compressed_tokens = count_tokens_approx(messages)
        if original_tokens > 0:
            savings = self.compressor.estimate_savings(original_tokens, compressed_tokens)
            if savings > 0:
                self.stats.total_tokens_saved = getattr(self.stats, "total_tokens_saved", 0) + (original_tokens - compressed_tokens)

        chain = self._resolve_chain(model, tier)
        if not chain:
            raise Exception("Köprü: aktif provider yok")

        last_err = ""
        self.stats.total_requests += 1
        tried = 0

        for base_url, api_key, m in chain:
            br = self._breaker(base_url)
            if br.should_skip():
                last_err = "circuit_open"
                continue

            tried += 1
            payload = {
                "model": m,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", 2048),
                "temperature": kwargs.get("temperature", 0.7),
                "stream": False,
            }
            try:
                r = requests.post(
                    f"{base_url}/chat/completions",
                    headers=self._headers(api_key, base_url),
                    json=payload, timeout=kwargs.get("timeout", 60),
                )
                if r.status_code >= 400:
                    last_err = self._classify(r.status_code)
                    # 4xx auth hatası → circuit açma (diğer provider'da da olur)
                    if last_err == "auth":
                        br.record_failure()
                        break
                    br.record_failure()
                    continue

                data = r.json()
                content = self._extract(data)
                if content:
                    br.record_success()
                    self.stats.successful += 1
                    self._count_tokens(data, base_url)
                    self.stats.fallback_used += (tried > 1)
                    return content
                last_err = "empty"
                br.record_failure()
                continue
            except requests.Timeout:
                last_err = "timeout"
                br.record_failure()
                continue
            except requests.RequestException as e:
                last_err = str(e)[:80]
                br.record_failure()
                continue

        self.stats.failed += 1
        self.stats.last_error = last_err
        raise Exception(f"Köprü: tüm provider'lar başarısız (son: {last_err})")

    # ── Streaming chat ───────────────────────────────────────────────────

    def chat_stream(self, messages: List[Dict], model: str = "",
                    tier: Optional[Tier] = None, **kwargs) -> Generator[str, None, None]:
        """Streaming sohbet — auto-fallback + circuit breaker + compression."""
        # Compression uygula
        original_tokens = count_tokens_approx(messages)
        messages = self.compressor.compress(messages, summarizer=kwargs.get("summarizer"))
        compressed_tokens = count_tokens_approx(messages)
        if original_tokens > 0:
            savings = self.compressor.estimate_savings(original_tokens, compressed_tokens)
            if savings > 0:
                self.stats.total_tokens_saved += (original_tokens - compressed_tokens)

        chain = self._resolve_chain(model, tier)
        if not chain:
            yield "❌ Köprü: aktif provider yok"
            return

        self.stats.total_requests += 1
        last_err = ""
        tried = 0

        for base_url, api_key, m in chain:
            br = self._breaker(base_url)
            if br.should_skip():
                last_err = "circuit_open"
                continue

            tried += 1
            payload = {
                "model": m,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", 2048),
                "temperature": kwargs.get("temperature", 0.7),
                "stream": True,
            }
            try:
                r = requests.post(
                    f"{base_url}/chat/completions",
                    headers=self._headers(api_key, base_url),
                    json=payload, timeout=kwargs.get("timeout", 60),
                    stream=True,
                )
                if r.status_code in (429, 402, 503):
                    last_err = str(r.status_code)
                    r.close()
                    br.record_failure()
                    self.stats.fallback_used += (tried > 1)
                    continue
                if r.status_code >= 400:
                    last_err = self._classify(r.status_code)
                    r.close()
                    br.record_failure()
                    continue

                got = False
                for line in r.iter_lines():
                    if not line:
                        continue
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        line = line[6:]
                    if line.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(line)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content") or delta.get("reasoning") or ""
                        if content:
                            got = True
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
                if got:
                    br.record_success()
                    self.stats.successful += 1
                    self.stats.fallback_used += (tried > 1)
                    return
                last_err = "empty"
                br.record_failure()
                continue
            except Exception as e:
                last_err = str(e)[:80]
                br.record_failure()
                continue

        self.stats.failed += 1
        self.stats.last_error = last_err
        yield f"❌ Köprü: tüm provider'lar başarısız (son: {last_err})"

    # ── Chain resolution (OmniRoute fallbackPolicy.ts benzeri) ────────────

    def _resolve_chain(self, model: str = "",
                       tier: Optional[Tier] = None) -> List[Tuple[str, str, str]]:
        """Fallback zincirini çöz — circuit açık olanları çıkar."""
        chain = resolve_model_chain(self.providers, model or self.default_model)
        # Circuit breaker açık olanları ele
        filtered = []
        for base_url, api_key, m in chain:
            br = self._breaker(base_url)
            if not br.should_skip():
                filtered.append((base_url, api_key, m))
        return filtered

    # ── Tag-based routing (OmniRoute tagRouter.ts benzeri) ────────────────

    def resolve_tier(self, tags: List[str]) -> Optional[Tier]:
        """Tag'a göre fitness tier seç (code → best-reasoning, simple → cheapest)."""
        tag_set = set(t.lower() for t in tags)
        if {"code", "reasoning", "complex"}.intersection(tag_set):
            return Tier.BEST_REASONING
        if {"simple", "cheap", "fast"}.intersection(tag_set):
            return Tier.CHEAPEST
        if tag_set:
            return Tier.MODERATE
        return None

    # ── Extract & stats ──────────────────────────────────────────────────

    def _extract(self, data: dict) -> str:
        try:
            msg = data["choices"][0]["message"]
            return msg.get("content") or msg.get("reasoning") or ""
        except (KeyError, IndexError, TypeError):
            return ""

    def _count_tokens(self, data: dict, base_url: str):
        try:
            u = data.get("usage", {})
            self.stats.total_tokens += u.get("total_tokens", 0)
            for p in self.providers:
                if p.base_url in base_url:
                    self.stats.per_provider[p.name] = \
                        self.stats.per_provider.get(p.name, 0) + 1
        except Exception:
            pass

    # ── Status / health (dashboard için) ─────────────────────────────────

    def health(self) -> Dict:
        """Provider sağlık durumu (circuit breaker dahil)."""
        out = {}
        for p in self.providers:
            br = self._breaker(p.base_url)
            out[p.name] = {
                "enabled": p.enabled,
                "priority": p.priority,
                "models": p.models,
                "healthy": not br.should_skip(),
                "failures": br.failures,
                "circuit_open": br.open,
            }
        return out

    def status(self) -> Dict:
        """İstatistik özeti."""
        return {
            "total_requests": self.stats.total_requests,
            "successful": self.stats.successful,
            "failed": self.stats.failed,
            "fallback_used": self.stats.fallback_used,
            "total_tokens": self.stats.total_tokens,
            "total_tokens_saved": self.stats.total_tokens_saved,
            "per_provider": self.stats.per_provider,
            "last_error": self.stats.last_error,
            "providers": len(self.providers),
        }
