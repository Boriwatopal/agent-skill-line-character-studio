#!/usr/bin/env python3
"""Store (or check) the user's OpenAI API key for this skill without ever printing it.

  python3 set_api_key.py            # user runs it in their own terminal: hidden prompt, nothing echoed
  printf %s "$KEY" | python3 set_api_key.py --stdin    # when the user pasted the key in chat
  python3 set_api_key.py --check    # is a working key already stored?

The key goes to <skill>/.env (chmod 600). It is verified with GET /v1/models, which costs nothing.
"""
from __future__ import annotations

import getpass
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENV = Path(__file__).resolve().parent.parent / ".env"


def stored_key() -> str | None:
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            if line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def verify(key: str) -> tuple[bool, str]:
    req = urllib.request.Request("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            ids = [m["id"] for m in json.load(r).get("data", [])]
        img = sorted(i for i in ids if i.startswith("gpt-image"))
        return True, f"key works; image models available: {', '.join(img) or 'none listed'}"
    except urllib.error.HTTPError as e:
        return False, f"OpenAI rejected the key (HTTP {e.code})"
    except Exception as e:                      # network problems etc.
        return False, f"could not reach OpenAI: {e}"


def main():
    if "--check" in sys.argv:
        key = stored_key()
        if not key:
            sys.exit("NO KEY STORED")
        ok, msg = verify(key)
        print(("OK: " if ok else "PROBLEM: ") + msg)
        sys.exit(0 if ok else 1)
    key = sys.stdin.read().strip() if "--stdin" in sys.argv else getpass.getpass("Paste your OpenAI API key (hidden): ").strip()
    if not key.startswith("sk-"):
        sys.exit("That doesn't look like an OpenAI key (they start with 'sk-'). Nothing saved.")
    ok, msg = verify(key)
    if not ok:
        sys.exit(f"Not saved: {msg}")
    ENV.write_text(f"OPENAI_API_KEY={key}\n")
    ENV.chmod(0o600)
    print(f"Saved to {ENV} (readable only by you). {msg}")


if __name__ == "__main__":
    main()
