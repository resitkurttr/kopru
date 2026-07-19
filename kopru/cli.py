#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Köprü CLI — Terminal'den hızlı sorgu.

Kullanım:
    python -m kopru.cli "Merhaba, nasılsın?"
    python -m kopru.cli --model deepseek/deepseek-chat "Python ile fibonacci yaz"
"""
import argparse
import sys
from .router import Router


def main():
    parser = argparse.ArgumentParser(prog="kopru", description="Köprü AI Gateway CLI")
    parser.add_argument("prompt", nargs="?", help="Gönderilecek mesaj")
    parser.add_argument("--model", "-m", default="", help="Model adı (opsiyonel)")
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--config", "-c", default=None, help="config.yaml yolu")
    parser.add_argument("--status", action="store_true", help="Durum raporu")
    args = parser.parse_args()

    router = Router(args.config)

    if args.status:
        import json
        print(json.dumps(router.status(), indent=2, ensure_ascii=False))
        return

    if not args.prompt:
        parser.print_help()
        sys.exit(1)

    try:
        for token in router.chat_stream(
            [{"role": "user", "content": args.prompt}],
            model=args.model,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        ):
            print(token, end="", flush=True)
        print()
    except Exception as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
