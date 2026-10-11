#!/usr/bin/env python3
"""Generate images with OpenAI GPT Image models (default: gpt-image-2).

Two modes, chosen automatically:
  - text-to-image  : no --image given  -> POST /v1/images/generations
  - image edit/ref : --image given     -> POST /v1/images/edits (keeps the subject)

Prompts come from a JSON file so a batch of N different variants runs in parallel.

JSON prompt file: either
  {"name1": "prompt text", "name2": "prompt text"}
or
  [{"name": "name1", "prompt": "..."}, ...]

Usage:
  python3 gen_images.py --prompts p.json --out out/
  python3 gen_images.py --prompts p.json --out out/ --image ref.png [--image ref2.png]
  ... [--base "shared prefix text"] [--size 1024x1536] [--quality high]
      [--model gpt-image-2] [--n 1] [--workers 4] [--background transparent]

API key resolution order: --api-key, $OPENAI_API_KEY, <this skill>/.env (written by set_api_key.py)
"""
import argparse, base64, json, os, sys, urllib.request, urllib.error, uuid, mimetypes
import concurrent.futures as cf
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
VALID_SIZES = {"1024x1024", "1024x1536", "1536x1024", "auto"}


def resolve_key(cli_key):
    if cli_key:
        return cli_key
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]
    env = SKILL_DIR / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("No API key. Ask the user for it and run scripts/set_api_key.py (see SKILL.md, Step 0).")


def load_prompts(path):
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict):
        return list(data.items())
    return [(d["name"], d["prompt"]) for d in data]


def post_json(url, payload, key):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.load(r)


def post_multipart(url, fields, files, key):
    b = uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for k, path in files:
        p = Path(path)
        ctype = mimetypes.guess_type(p.name)[0] or "image/png"
        parts.append(
            f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{p.name}"\r\n'
            f'Content-Type: {ctype}\r\n\r\n'.encode() + p.read_bytes() + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    req = urllib.request.Request(
        url, data=b"".join(parts),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": f"multipart/form-data; boundary={b}"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.load(r)


def run_one(name, prompt, a, key):
    try:
        if a.image:
            fields = {"model": a.model, "prompt": prompt, "size": a.size,
                      "quality": a.quality, "n": str(a.n)}
            if a.background:
                fields["background"] = a.background
            files = [("image[]", p) for p in a.image] if len(a.image) > 1 else [("image", a.image[0])]
            if a.mask:
                files.append(("mask", a.mask))
            j = post_multipart("https://api.openai.com/v1/images/edits", fields, files, key)
        else:
            payload = {"model": a.model, "prompt": prompt, "size": a.size,
                       "quality": a.quality, "n": a.n}
            if a.background:
                payload["background"] = a.background
            j = post_json("https://api.openai.com/v1/images/generations", payload, key)
    except urllib.error.HTTPError as e:
        return f"ERR  {name}: HTTP {e.code} {e.read()[:500].decode(errors='replace')}"
    except Exception as e:
        return f"ERR  {name}: {e}"

    outs = []
    for i, d in enumerate(j.get("data", [])):
        suffix = "" if a.n == 1 else f"_{i+1}"
        out = Path(a.out) / f"{name}{suffix}.png"
        out.write_bytes(base64.b64decode(d["b64_json"]))
        outs.append(str(out))
    return "OK   " + ", ".join(outs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", required=True, help="JSON file of {name: prompt}")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--image", action="append", default=[],
                    help="reference image (repeatable); triggers edit mode")
    ap.add_argument("--mask", help="optional mask PNG for inpainting (edit mode)")
    ap.add_argument("--base", default="", help="shared text prefixed to every prompt")
    ap.add_argument("--model", default="gpt-image-2")
    ap.add_argument("--size", default="1024x1024")
    ap.add_argument("--quality", default="high", choices=["low", "medium", "high", "auto"])
    ap.add_argument("--background", choices=["transparent", "opaque", "auto"])
    ap.add_argument("--n", type=int, default=1, help="images per prompt")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--api-key")
    a = ap.parse_args()

    if a.size not in VALID_SIZES:
        sys.exit(f"--size must be one of {sorted(VALID_SIZES)}")
    key = resolve_key(a.api_key)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    prompts = load_prompts(a.prompts)
    print(f"{len(prompts)} prompt(s) -> {a.out}  "
          f"[{a.model} {a.size} {a.quality} {'edit' if a.image else 'generate'}]", flush=True)

    failed = 0
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(run_one, n, a.base + p, a, key): n for n, p in prompts}
        for f in cf.as_completed(futs):
            line = f.result()
            if line.startswith("ERR"):
                failed += 1
            print(line, flush=True)
    if failed:
        sys.exit(f"{failed} of {len(prompts)} failed")


if __name__ == "__main__":
    main()
