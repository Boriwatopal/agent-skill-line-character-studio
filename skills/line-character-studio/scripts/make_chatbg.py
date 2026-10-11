#!/usr/bin/env python3
"""Turn square chat-background scenes into LINE's i_22 (iOS 1482x1334) and a_22 (Android 1300x1300),
each under 1 MB, and lay the candidates side by side in phone mockups.

Usage: make_chatbg.py OUT_DIR SHEET.png SCENE.png [SCENE.png ...]
"""
import io
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import theme_preview as tp      # reuse the chat-room phone mockup

MAX_BYTES = 1_000_000


def save_under_limit(im: Image.Image, path: Path) -> str:
    """Lossless PNG if it fits, else the richest dithered palette that fits under LINE's 1 MB."""
    im = im.convert("RGB")
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    if buf.tell() <= MAX_BYTES:
        path.write_bytes(buf.getvalue())
        return f"full colour, {buf.tell() / 1024:.0f} KB"
    for colors in (256, 224, 192, 160, 128, 96):
        q = im.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
        buf = io.BytesIO()
        q.save(buf, "PNG", optimize=True)
        if buf.tell() <= MAX_BYTES:
            path.write_bytes(buf.getvalue())
            return f"{colors}-colour palette, {buf.tell() / 1024:.0f} KB"
    raise SystemExit(f"{path.name}: cannot get under 1 MB")


def ios_canvas(sq: Image.Image, scene_px: int = 1240) -> Image.Image:
    """1482x1334, bottom-aligned. iPhone portrait shows only the centre 640px, so the scene is scaled
    until the flying bike fits that column; the extra edges (seen only in landscape) are mirrored."""
    W, H = 1482, 1334
    s = sq.resize((scene_px, scene_px), Image.LANCZOS)
    side, top = (W - scene_px) // 2, H - scene_px
    out = Image.new("RGB", (W, H))
    out.paste(s, (side, top))
    out.paste(s.crop((0, 0, side, scene_px)).transpose(Image.FLIP_LEFT_RIGHT), (0, top))
    right = W - side - scene_px
    out.paste(s.crop((scene_px - right, 0, scene_px, scene_px)).transpose(Image.FLIP_LEFT_RIGHT), (side + scene_px, top))
    if top:
        out.paste(out.crop((0, top, W, 2 * top)).transpose(Image.FLIP_TOP_BOTTOM), (0, 0))
    return out


def build(scene: Path, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    sq = Image.open(scene).convert("RGB")
    ios = ios_canvas(sq)
    android = sq.resize((1300, 1300), Image.LANCZOS)   # phones show ~1080 of 1300, so the bike fits as is
    top = np.asarray(ios)[:6].reshape(-1, 3).mean(axis=0).astype(int)
    return {"i_22": save_under_limit(ios, out / "i_22.png"),
            "a_22": save_under_limit(android, out / "a_22.png"),
            "top_colour": "#%02X%02X%02X" % tuple(top)}


def main(out_dir: str, sheet_path: str, scenes: list[str]):
    out = Path(out_dir)
    phones = []
    for s in scenes:
        s = Path(s)
        info = build(s, out / s.stem)
        print(s.stem, info)
        phones.append((s.stem.replace("chatbg-", ""), tp.chat_mockup(out / s.stem), info["top_colour"],
                       Image.open(out / s.stem / "a_22.png").convert("RGB")))
    pw, ph = phones[0][1].size
    sheet = Image.new("RGB", (len(phones) * (pw + 60) + 60, ph + 330), (243, 245, 249))
    d = ImageDraw.Draw(sheet)
    for k, (name, phone, top, android) in enumerate(phones):
        x = 60 + k * (pw + 60)
        d.text((x, 24), f"{k + 1}. {name}", font=tp.F(24, True), fill=tp.INK)
        sheet.paste(phone, (x, 70), phone)
        sheet.paste(android.resize((200, 200), Image.LANCZOS), (x, ph + 100))
        d.text((x + 216, ph + 110), "Android a_22", font=tp.F(16), fill=tp.MUTED)
        d.text((x + 216, ph + 136), f"top colour {top}", font=tp.F(16), fill=tp.MUTED)
    sheet.save(sheet_path, optimize=True)
    print(sheet_path, sheet.size)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
