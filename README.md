# Köprü — Özgün AI Gateway

> Çoklu AI sağlayıcısını tek endpoint'te birleştiren, otomatik fallback'li, açık kaynaklı AI gateway.
> OmniRoute'dan ilham alınarak **bağımsız ve özgün** olarak yazılmıştır.

## 🌉 Neden Köprü?

- **Tek endpoint**: `http://localhost:20128/v1/chat/completions` — OpenAI uyumlu
- **Otomatik fallback**: Ana model çökerse sıradaki provider'a geçer
- **Provider zinciri**: OpenRouter → OpenCode Zen → Ollama (priority sıralı)
- **Dashboard**: Tarayıcıdan provider durumunu gör, test sorgusu gönder
- **Sıfır bağımlılık**: Sadece Python + FastAPI

## 🚀 Hızlı Başlangıç

```bash
# 1. Klonla
git clone https://github.com/resitkurttr/kopru.git
cd kopru

# 2. Sanal ortam + bağımlılıklar
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. API key'leri ayarla (config.yaml env'den okur)
export OPENROUTER_API_KEY="sk-or-..."
export OPENCODE_ZEN_API_KEY="..."

# 4. Çalıştır (port 20128)
python -m kopru.gateway
# veya
uvicorn kopru.gateway:app --host 0.0.0.0 --port 20128
```

## 🖥️ Dashboard

Tarayıcıda aç: **http://localhost:20128/dashboard**

- Provider sağlık durumu (canlı)
- Model seçimi + test sorgusu
- İstatistikler (istek sayısı, fallback kullanımı)

## 💻 CLI Kullanımı

```bash
python -m kopru.cli "Merhaba, nasılsın?"
python -m kopru.cli --model deepseek/deepseek-chat "Fibonacci yaz"
python -m kopru.cli --status
```

## 🔌 Claude Code / Cursor / OpenCode Entegrasyonu

`config.yaml`'daki `base_url` yerine:

```
http://localhost:20128/v1
```

API key boş bırakılabilir (provider'a göre).

## 📁 Yapı

```
kopru/
├── kopru/
│   ├── gateway.py    # FastAPI app (/v1/chat/completions)
│   ├── router.py     # Auto-fallback mantığı
│   ├── config.py     # Provider config yükleme
│   ├── cli.py        # Terminal arayüzü
│   └── __init__.py
├── web/static/dashboard.html   # Web dashboard
├── config.yaml      # Provider ayarları (env tabanlı)
├── requirements.txt
└── README.md
```

## 🔧 Yeni Provider Ekleme

`config.yaml`'a:

```yaml
providers:
  - name: benim-providerim
    base_url: https://api.example.com/v1
    api_key: ${BENIM_API_KEY}
    priority: 15
    models: ["model-a", "model-b"]
```

## 📜 Lisans

MIT
