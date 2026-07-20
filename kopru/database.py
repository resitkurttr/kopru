# -*- coding: utf-8 -*-
"""
Köprü — Veritabanı Katmanı (SQLite)
API key'ler, provider'lar, kullanım takibi.
"""
import sqlite3
import os
import time
import secrets
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kopru.db"


def _ensure_db_dir():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_db():
    """Thread-safe SQLite bağlantısı."""
    _ensure_db_dir()
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Tabloları oluştur."""
    with get_db() as conn:
        conn.executescript("""
            -- API Keys
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_hash TEXT UNIQUE NOT NULL,
                key_prefix TEXT NOT NULL,
                name TEXT DEFAULT '',
                user_id TEXT DEFAULT '',
                enabled INTEGER DEFAULT 1,
                rate_limit INTEGER DEFAULT 60,
                created_at REAL NOT NULL,
                last_used_at REAL DEFAULT 0,
                total_requests INTEGER DEFAULT 0
            );

            -- Providers (dynamic)
            CREATE TABLE IF NOT EXISTS providers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                base_url TEXT NOT NULL,
                api_key TEXT DEFAULT '',
                models TEXT DEFAULT '[]',
                priority INTEGER DEFAULT 0,
                enabled INTEGER DEFAULT 1,
                category TEXT DEFAULT 'general',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

            -- Usage logs
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key_id INTEGER,
                provider_name TEXT,
                model TEXT,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                latency_ms INTEGER DEFAULT 0,
                status_code INTEGER DEFAULT 200,
                error TEXT DEFAULT '',
                created_at REAL NOT NULL,
                FOREIGN KEY (api_key_id) REFERENCES api_keys(id)
                    ON DELETE SET NULL
            );

            -- Provider health cache
            CREATE TABLE IF NOT EXISTS provider_health (
                provider_name TEXT PRIMARY KEY,
                healthy INTEGER DEFAULT 1,
                failures INTEGER DEFAULT 0,
                last_check REAL DEFAULT 0,
                avg_latency_ms INTEGER DEFAULT 0,
                circuit_open INTEGER DEFAULT 0
            );

            -- Indexes
            CREATE INDEX IF NOT EXISTS idx_usage_api_key ON usage_logs(api_key_id);
            CREATE INDEX IF NOT EXISTS idx_usage_created ON usage_logs(created_at);
            CREATE INDEX IF NOT EXISTS idx_usage_provider ON usage_logs(provider_name);
        """)


# ── API Key CRUD ──────────────────────────────────────────────────────────────

def create_api_key(name: str = "", user_id: str = "",
                   rate_limit: int = 60) -> Dict[str, Any]:
    """Yeni API key üret. {key: "kp_xxx...", ...} döndür."""
    raw_key = f"kp_{secrets.token_hex(24)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:12] + "..."
    now = time.time()

    with get_db() as conn:
        conn.execute(
            "INSERT INTO api_keys (key_hash, key_prefix, name, user_id, "
            "rate_limit, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (key_hash, key_prefix, name, user_id, rate_limit, now)
        )
        row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    return {
        "id": row_id,
        "key": raw_key,
        "key_prefix": key_prefix,
        "name": name,
        "user_id": user_id,
        "rate_limit": rate_limit,
        "created_at": now,
    }


def verify_api_key(raw_key: str) -> Optional[Dict]:
    """API key doğrula. Geçerliyse key bilgilerini döndür."""
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM api_keys WHERE key_hash = ? AND enabled = 1",
            (key_hash,)
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE api_keys SET last_used_at = ?, "
                "total_requests = total_requests + 1 WHERE id = ?",
                (time.time(), row["id"])
            )
            return dict(row)
    return None


def list_api_keys() -> List[Dict]:
    """Tüm API key'leri listele (key值 gizli)."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, key_prefix, name, user_id, enabled, rate_limit, "
            "created_at, last_used_at, total_requests FROM api_keys "
            "ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def revoke_api_key(key_id: int) -> bool:
    """API key'i devre dışı bırak."""
    with get_db() as conn:
        conn.execute("UPDATE api_keys SET enabled = 0 WHERE id = ?", (key_id,))
        return conn.execute("SELECT changes()").fetchone()[0] > 0


def delete_api_key(key_id: int) -> bool:
    """API key'i tamamen sil."""
    with get_db() as conn:
        conn.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
        return conn.execute("SELECT changes()").fetchone()[0] > 0


# ── Provider CRUD ─────────────────────────────────────────────────────────────

def create_provider(name: str, base_url: str, api_key: str = "",
                    models: List[str] = None, priority: int = 0,
                    category: str = "general") -> Dict:
    """Yeni provider ekle."""
    import json
    now = time.time()
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM providers WHERE name = ?", (name,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE providers SET base_url = ?, api_key = ?, models = ?, "
                "priority = ?, category = ?, updated_at = ? WHERE name = ?",
                (base_url, api_key, json.dumps(models or []),
                 priority, category, now, name)
            )
            row_id = existing["id"]
        else:
            conn.execute(
                "INSERT INTO providers (name, base_url, api_key, models, "
                "priority, category, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (name, base_url, api_key, json.dumps(models or []),
                 priority, category, now, now)
            )
            row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"id": row_id, "name": name, "base_url": base_url}


def list_providers() -> List[Dict]:
    """Tüm provider'ları listele."""
    import json
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM providers ORDER BY priority ASC"
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["models"] = json.loads(d["models"])
            result.append(d)
        return result


def update_provider(provider_id: int, **kwargs) -> bool:
    """Provider güncelle."""
    import json
    allowed = {"name", "base_url", "api_key", "models", "priority",
               "enabled", "category"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return False
    if "models" in updates and isinstance(updates["models"], list):
        updates["models"] = json.dumps(updates["models"])
    updates["updated_at"] = time.time()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [provider_id]
    with get_db() as conn:
        conn.execute(
            f"UPDATE providers SET {set_clause} WHERE id = ?", values
        )
        return conn.execute("SELECT changes()").fetchone()[0] > 0


def delete_provider(provider_id: int) -> bool:
    """Provider sil."""
    with get_db() as conn:
        conn.execute("DELETE FROM providers WHERE id = ?", (provider_id,))
        return conn.execute("SELECT changes()").fetchone()[0] > 0


def get_provider_by_name(name: str) -> Optional[Dict]:
    """İsme göre provider bul."""
    import json
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM providers WHERE name = ?", (name,)
        ).fetchone()
        if row:
            d = dict(row)
            d["models"] = json.loads(d["models"])
            return d
    return None


# ── Usage Tracking ────────────────────────────────────────────────────────────

def log_usage(api_key_id: Optional[int], provider_name: str, model: str,
              input_tokens: int = 0, output_tokens: int = 0,
              latency_ms: int = 0, status_code: int = 200,
              error: str = ""):
    """Kullanım kaydı oluştur."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO usage_logs (api_key_id, provider_name, model, "
            "input_tokens, output_tokens, latency_ms, status_code, "
            "error, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (api_key_id, provider_name, model, input_tokens, output_tokens,
             latency_ms, status_code, error, time.time())
        )


def get_usage_stats(days: int = 7) -> Dict:
    """Son N günün kullanım istatistikleri."""
    since = time.time() - (days * 86400)
    with get_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) as cnt, "
            "COALESCE(SUM(input_tokens), 0) as in_tok, "
            "COALESCE(SUM(output_tokens), 0) as out_tok, "
            "COALESCE(AVG(latency_ms), 0) as avg_lat "
            "FROM usage_logs WHERE created_at > ?", (since,)
        ).fetchone()

        by_provider = conn.execute(
            "SELECT provider_name, COUNT(*) as cnt, "
            "COALESCE(SUM(input_tokens + output_tokens), 0) as tokens "
            "FROM usage_logs WHERE created_at > ? "
            "GROUP BY provider_name ORDER BY cnt DESC",
            (since,)
        ).fetchall()

        by_model = conn.execute(
            "SELECT model, COUNT(*) as cnt "
            "FROM usage_logs WHERE created_at > ? "
            "GROUP BY model ORDER BY cnt DESC LIMIT 10",
            (since,)
        ).fetchall()

        errors = conn.execute(
            "SELECT COUNT(*) as cnt FROM usage_logs "
            "WHERE created_at > ? AND status_code >= 400",
            (since,)
        ).fetchone()

    return {
        "period_days": days,
        "total_requests": total["cnt"],
        "total_tokens": total["in_tok"] + total["out_tok"],
        "input_tokens": total["in_tok"],
        "output_tokens": total["out_tok"],
        "avg_latency_ms": round(total["avg_lat"]),
        "error_count": errors["cnt"],
        "by_provider": [dict(r) for r in by_provider],
        "by_model": [dict(r) for r in by_model],
    }


# ── Provider Health ───────────────────────────────────────────────────────────

def update_provider_health(name: str, healthy: bool, failures: int = 0,
                           avg_latency_ms: int = 0, circuit_open: bool = False):
    """Provider sağlık durumunu güncelle."""
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO provider_health "
            "(provider_name, healthy, failures, last_check, "
            "avg_latency_ms, circuit_open) VALUES (?, ?, ?, ?, ?, ?)",
            (name, int(healthy), failures, time.time(),
             avg_latency_ms, int(circuit_open))
        )


def get_provider_health() -> Dict[str, Dict]:
    """Tüm provider sağlık durumlarını getir."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM provider_health").fetchall()
        return {r["provider_name"]: dict(r) for r in rows}


# Initialize on import
init_db()
