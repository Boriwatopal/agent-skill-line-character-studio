#!/usr/bin/env python3
"""Trim stickers to content + 10px margin (even sizes, <= 370x320), validate LINE specs, copy + zip.

Usage: finalize_line.py SRC_DIR DEST_DIR ZIP_PATH
"""
import sys
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

MARGIN, MAX_W, MAX_H, MAX_BYTES = 10, 370, 320, 1_000_000
FIXED = {"main.png": (240, 240), "tab.png": (96, 74)}


def trim_even(im: Image.Image) -> Image.Image:
    a = np.asarray(im.getchannel("A"))
    ys, xs = np.nonzero(a > 0)
    l, t = max(0, xs.min() - MARGIN), max(0, ys.min() - MARGIN)
    r, b = min(im.width, xs.max() + 1 + MARGIN), min(im.height, ys.max() + 1 + MARGIN)
    if (r - l) % 2:
        r, l = (r + 1, l) if r < im.width else (r, l - 1)
    if (b - t) % 2:
        b, t = (b + 1, t) if b < im.height else (b, t - 1)
    return im.crop((l, t, r, b))


def check(path: Path) -> list[str]:
    im = Image.open(path)
    w, h = im.size
    a = np.asarray(im.convert("RGBA").getchannel("A"))
    problems = []
    if path.name in FIXED:
        if (w, h) != FIXED[path.name]:
            problems.append(f"size {w}x{h} != {FIXED[path.name]}")
    else:
        if w > MAX_W or h > MAX_H:
            problems.append(f"too big {w}x{h}")
        if w % 2 or h % 2:
            problems.append(f"odd size {w}x{h}")
        ys, xs = np.nonzero(a > 0)
        m = (xs.min(), ys.min(), w - 1 - xs.max(), h - 1 - ys.max())
        if min(m) < MARGIN - 1:
            problems.append(f"margin {m}")
    if im.mode not in ("RGBA", "RGB", "P"):
        problems.append(f"mode {im.mode}")
    if a.min() != 0:
        problems.append("no transparency")
    if path.stat().st_size > MAX_BYTES:
        problems.append(f"{path.stat().st_size} bytes")
    return problems


def main(src: Path, dest: Path, zip_path: Path):
    dest.mkdir(parents=True, exist_ok=True)
    names = sorted(p.name for p in src.glob("[0-9][0-9].png")) + ["main.png", "tab.png"]
    for n in names:
        im = Image.open(src / n).convert("RGBA")
        if n not in FIXED:
            im = trim_even(im)
        im.save(dest / n, optimize=True)
    bad = 0
    for n in names:
        p = dest / n
        probs = check(p)
        bad += bool(probs)
        print(f"{n:9} {Image.open(p).size!s:12} {p.stat().st_size / 1024:6.1f} KB  {'OK' if not probs else probs}")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.write(dest / n, arcname=n)          # flat: no folders inside the ZIP
    print(f"\n{len(names)} files, {bad} with problems -> {zip_path} ({zip_path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
