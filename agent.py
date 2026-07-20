#!/usr/bin/env python3
"""
Köpré Ajan — Minimal chat bot
Kullanım: python3 agent.py <api_key> [model]
"""
import sys, json, urllib.request, urllib.error

GATEWAY = "http://localhost:20128"

def chat(api_key, messages, model="gpt-3.5-turbo"):
    url = f"{GATEWAY}/v1/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": 500,
        "temperature": 0.7,
    }).encode()

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")

    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]

def main():
    if len(sys.argv) < 2:
        print("Kullanım: python3 agent.py <api_key> [model]")
        sys.exit(1)

    api_key = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "gpt-3.5-turbo"
    messages = [{"role": "system", "content": "Sen yardımcı bir asistansın. Kısa ve net cevaplar ver."}]

    print(f"🤖 Köpré Ajan | Model: {model}")
    print(f"🔑 Key: {api_key[:12]}...{api_key[-4:]}")
    print("📝 Mesaj yaz, Enter'a bas (çıkış: q)\n")

    while True:
        try:
            user_input = input("Sen: ").strip()
            if user_input.lower() in ("q", "quit", "exit", "çıkış"):
                print("Hoşça kal!")
                break
            if not user_input:
                continue

            messages.append({"role": "user", "content": user_input})
            reply = chat(api_key, messages, model)
            messages.append({"role": "assistant", "content": reply})

            print(f"Ajan: {reply}\n")
        except KeyboardInterrupt:
            print("\nHoşça kal!")
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"❌ HTTP {e.code}: {body}\n")
        except Exception as e:
            print(f"❌ Hata: {e}\n")

if __name__ == "__main__":
    main()
