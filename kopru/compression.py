# -*- coding: utf-8 -*-
"""
Köprü — Token Sıkıştırma (OmniRoute RTK/Caveman esinli)

Bağlam penceresini küçültmek için eski mesajları özetler.
Basit ama etkili: mesaj sayısı eşiği aşınca en eski N mesajı
tek bir özet mesajına indirger.

OmniRoute'un "RTK + Caveman" (%15-95 tasarruf) mantığının
hafif Python karşılığı — judge model yerine yerinde özet.
"""
from typing import Dict, List


class Compressor:
    """
    Mesaj dizisini sıkıştırır.

    Stratejiler:
      - none:    sıkıştırma yok
      - simple:  eski mesajları tek özet mesajına indirger
      - aggressive: system dışı her şeyi sıkıştırır
    """

    def __init__(self, strategy: str = "simple", threshold: int = 10,
                 keep_recent: int = 4):
        self.strategy = strategy
        self.threshold = threshold
        self.keep_recent = keep_recent

    def compress(self, messages: List[Dict],
                 summarizer=None) -> List[Dict]:
        """
        messages: [{"role": ..., "content": ...}, ...]
        summarizer: optional callable(list[Dict]) -> str (özet üretir)

        Dönüş: sıkıştırılmış mesaj listesi
        """
        if self.strategy == "none":
            return messages

        if len(messages) <= self.threshold:
            return messages

        # System mesajlarını ayır (korunur)
        system_msgs = [m for m in messages if m.get("role") == "system"]
        others = [m for m in messages if m.get("role") != "system"]

        if len(others) <= self.keep_recent:
            return messages

        # Sıkıştırılacak eski mesajlar
        to_compress = others[: len(others) - self.keep_recent]
        recent = others[len(others) - self.keep_recent:]

        # Özet üret
        if summarizer:
            summary = summarizer(to_compress)
        else:
            summary = self._fallback_summary(to_compress)

        summary_msg = {
            "role": "system",
            "content": f"[Önceki konuşma özeti — sıkıştırıldı]\n{summary}",
        }

        return system_msgs + [summary_msg] + recent

    def _fallback_summary(self, msgs: List[Dict]) -> str:
        """Summarizer yoksa basit çıkarım: kullanıcı sorularını listele."""
        parts = []
        for m in msgs:
            role = m.get("role", "?")
            content = m.get("content", "")
            if isinstance(content, list):
                # multimodal — text kısmını al
                content = " ".join(
                    p.get("text", "") for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                )
            # Sadece ilk 80 karakter — özet kısa olsun
            snippet = content[:80].replace("\n", " ").strip()
            if snippet:
                parts.append(f"{role[0]}:{snippet}")
        return " | ".join(parts) if parts else "(boş konuşma)"

    def estimate_savings(self, before: int, after: int) -> float:
        """Yüzde tasarruf."""
        if before == 0:
            return 0.0
        return round((1 - after / before) * 100, 1)


def count_tokens_approx(messages: List[Dict]) -> int:
    """Yaklaşık token sayısı (~4 char/token)."""
    total = 0
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, list):
            content = " ".join(p.get("text", "") for p in content
                               if isinstance(p, dict))
        total += len(str(content)) // 4
    return total
