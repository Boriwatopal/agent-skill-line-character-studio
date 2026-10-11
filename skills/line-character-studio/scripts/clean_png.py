#!/usr/bin/env python3
"""Tidy gpt-image transparent PNGs for slide use.

- near-opaque pixels (alpha >= 230) -> fully opaque, so the mascot isn't faintly see-through
- RGB under fully transparent pixels -> white, so viewers that ignore alpha show no coloured glow
- trim empty margins, keeping PAD px of breathing room except on sides where the art
  touches the canvas edge (e.g. the peek-from-bottom pose stays flush to its bottom edge)

Usage: clean_png.py OUT_DIR IN.png [IN.png ...]
       clean_png.py OUT_DIR IN.png --cut-bottom ROW   (drop rows >= ROW, trim flush there)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

PAD = 24
SOLID = 230
EDGE_ALPHA = 16  # alpha at or below this counts as empty when finding the trim box


def clean(src: Path, out_dir: Path, cut_bottom: int | None = None) -> str:
    a = np.array(Image.open(src).convert("RGBA"))
    alpha = a[..., 3]
    alpha[alpha >= SOLID] = 255
    if cut_bottom is not None:
        alpha[cut_bottom:] = 0
    a[alpha == 0, :3] = 255

    ys, xs = np.nonzero(alpha > EDGE_ALPHA)
    h, w = alpha.shape
    top, bottom, left, right = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    top = top if top <= 2 else max(0, top - PAD)
    left = left if left <= 2 else max(0, left - PAD)
    if cut_bottom is None:
        bottom = bottom if bottom >= h - 2 else min(h, bottom + PAD)
    right = right if right >= w - 2 else min(w, right + PAD)

    im = Image.fromarray(a[top:bottom, left:right])
    dst = out_dir / src.name
    im.save(dst, optimize=True)
    return f"{src.name}: {w}x{h} -> {im.width}x{im.height}"


if __name__ == "__main__":
    args = sys.argv[2:]
    cut = None
    if "--cut-bottom" in args:
        i = args.index("--cut-bottom")
        cut = int(args[i + 1])
        del args[i:i + 2]
    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    for p in args:
        print(clean(Path(p), out_dir, cut))
