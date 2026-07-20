#!/usr/bin/env python3
"""
Köpré Test Ajanı — Minimal API key testi
Kullanım: python3 test_agent.py <api_key>
"""
import sys, json, urllib.request, urllib.error

GATEWAY = "http://localhost:20128"  # Köpré gateway

def chat(api_key, message, model="gpt-3.5-turbo"):
    """Köpré gateway üzerinden chat completion isteği gönder."""
    url = f"{GATEWAY}/v1/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "max_tokens": 150,
        "temperature": 0.7,
    }).encode()

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return {
                "model": data.get("model", model),
                "reply": data["choices"][0]["message"]["content"],
                "usage": data.get("usage", {}),
            }
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"error": str(e)}

def health():
    """Gateway sağlık kontrolü."""
    url = f"{GATEWAY}/health"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.loads(resp.read())
    except:
        return {"status": "unreachable"}

if __name__ == "__main__":
    # Sağlık kontrolü
    h = health()
    if h.get("status") != "running":
        print("❌ Köpré gateway çalışmıyor!")
        print("   Başlat: cd kopru && .venv/bin/uvicorn kopru.gateway:app --host 0.0.0.0 --port 20128")
        sys.exit(1)
    print("✅ Köpré gateway çalışıyor")

    if len(sys.argv) < 2:
        print("Kullanım: python3 test_agent.py <api_key>")
        sys.exit(1)

    key = sys.argv[1]
    print(f"\n🔑 Test ediliyor: {key[:12]}...{key[-4:]}")
    print(f"📝 Mesaj: 'Merhaba! Sen kimsin?'")
    print()

    result = chat(key, "Merhaba! Sen kimsin? Lütfen kendini tanıta kısa bir cevap ver.")

    if "error" in result:
        print(f"❌ Hata: {result['error']}")
    else:
        print(f"✅ Model: {result['model']}")
        print(f"💬 Yanıt: {result['reply']}")
        if result.get("usage"):
            print(f"📊 Token: {result['usage'].get('total_tokens', '?')}")
