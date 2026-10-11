#!/usr/bin/env python3
"""Validate a LINE theme image folder against the Creators Market spec and build the flat upload ZIP.

Usage: finalize_theme.py THEME_DIR ZIP_PATH
"""
import sys
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

TAB_IDS = [3, 4, 7, 8, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38]
EXPECTED = {
    "ios_thumbnail.png": (200, 284), "android_thumbnail.png": (136, 202), "store_thumbnail.png": (198, 278),
    **{f"i_{i:02d}.png": (128, 150) for i in TAB_IDS},
    **{f"i_{i:02d}_g.png": (80, 56) for i in TAB_IDS},
    "i_11.png": (1472, 150),
    **{f"i_{i}.png": (120, 120) for i in range(12, 20)},
    **{f"a_{i}.png": (116, 116) for i in range(12, 20)},
    "i_20.png": (240, 240), "i_21.png": (240, 240), "a_20.png": (247, 247), "a_21.png": (247, 247),
    "i_22.png": (1482, 1334), "a_22.png": (1300, 1300),
}
MUST_BE_OPAQUE = {"ios_thumbnail.png", "android_thumbnail.png", "store_thumbnail.png",
                  "i_20.png", "i_21.png", "a_20.png", "a_21.png"}
MAX_BYTES = 1_000_000


def check(p: Path, size) -> list[str]:
    probs = []
    im = Image.open(p)
    if im.format != "PNG":
        probs.append(f"format {im.format}")
    if im.size != size:
        probs.append(f"size {im.size} != {size}")
    if p.name in MUST_BE_OPAQUE and im.mode == "RGBA" and np.asarray(im)[..., 3].min() < 255:
        probs.append("has transparency")
    if p.stat().st_size > MAX_BYTES:
        probs.append(f"{p.stat().st_size / 1e6:.2f} MB")
    return probs


def main(theme_dir: str, zip_path: str):
    d, z = Path(theme_dir), Path(zip_path)
    missing = [n for n in EXPECTED if not (d / n).exists()]
    extra = sorted(p.name for p in d.glob("*.png") if p.name not in EXPECTED)
    bad = {n: check(d / n, s) for n, s in EXPECTED.items() if (d / n).exists()}
    bad = {n: v for n, v in bad.items() if v}
    print(f"expected {len(EXPECTED)}, missing {missing or 'none'}, extra {extra or 'none'}")
    for n, v in bad.items():
        print("  PROBLEM", n, v)
    if missing or bad:
        sys.exit("not packaged")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for n in EXPECTED:
            zf.write(d / n, arcname=n)                  # flat ZIP, LINE's exact file names
    sizes = sorted(((d / n).stat().st_size, n) for n in EXPECTED)
    print(f"OK: {len(EXPECTED)} images, largest {sizes[-1][1]} {sizes[-1][0] / 1024:.0f} KB -> {z} ({z.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
