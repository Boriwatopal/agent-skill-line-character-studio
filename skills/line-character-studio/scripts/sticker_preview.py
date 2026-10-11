#!/usr/bin/env python3
"""Grid preview of LINE stickers on a chat-like background (light or dark), with numbers.

Usage: sticker_preview.py STICKER_DIR OUT.png [light|dark] [scale]
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BG = {"light": (140, 171, 216), "dark": (30, 30, 30)}     # LINE-ish default chat backgrounds
INK = {"light": (255, 255, 255), "dark": (170, 170, 170)}


def main(src: Path, out: Path, theme: str = "light", scale: float = 0.75):
    files = sorted(src.glob("[0-9][0-9].png"))
    cw, ch = int(370 * scale), int(320 * scale)
    pad, label_h, cols = 16, 26, 6
    rows = (len(files) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (cw + pad) + pad, rows * (ch + label_h + pad) + pad), BG[theme])
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    for i, p in enumerate(files):
        x = pad + (i % cols) * (cw + pad)
        y = pad + (i // cols) * (ch + label_h + pad)
        im = Image.open(p).convert("RGBA")
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        sheet.paste(im, (x + (cw - im.width) // 2, y + label_h + (ch - im.height) // 2), im)
        d.text((x + 4, y + 2), p.stem, font=f, fill=INK[theme])
    sheet.save(out, optimize=True)
    print(out, sheet.size)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), *(sys.argv[3:4] or ["light"]),
         *([float(sys.argv[4])] if len(sys.argv) > 4 else []))
