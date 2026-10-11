#!/usr/bin/env python3
"""Build every image of a LINE Creators Market theme from the mascot art (sizes per the
LINE theme guidelines, checked 2026-09-25).

Usage: make_theme.py SRC_DIR OUT_DIR [--primary "#0088F8"] [--secondary "#F8F808"]
SRC_DIR holds trimmed transparent PNGs: tab-<name>.png (9 menu busts), head-<mood>.png
(happy/wink/surprised/laughing), hero.png (full-body pose for thumbnails) and, optionally,
peek.png (peek-from-bottom pose, body cut flat) for the default chat background.
--primary: brand colour used for thumbnails/group profile/ledges; --secondary: light colour for
the single profile image (it is paled automatically).
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

S = 4                                           # supersampling for everything drawn in code
BLUE, BLACK, WHITE = (0, 136, 248), (0, 0, 0), (255, 255, 255)
LINE_W = 9                                      # art outline weight at ~1024px source scale

# tab name -> (OFF file id, ON file id); ids are LINE's fixed file names i_XX(.png|_g.png)
TABS = {"home": (29, 30), "chats": (3, 4), "voom": (33, 34), "shopping": (35, 36), "calls": (7, 8),
        "news": (25, 26), "today": (31, 32), "wallet": (27, 28), "apps": (37, 38)}
HEADS = ["happy", "wink", "surprised", "laughing"]          # passcode digits 1-4


SECONDARY = (248, 248, 8)


def hex_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lighten(c, t: float) -> tuple:
    """Mix colour c toward white by fraction t."""
    return tuple(round(v + (255 - v) * t) for v in c)


# ---------- low-level helpers ----------

def trim(im: Image.Image) -> Image.Image:
    return im.crop(im.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox())


def downsample(big: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Premultiplied LANCZOS resize; drops invisible haze so transparent pixels stay clean."""
    small = big.convert("RGBa").resize(size, Image.LANCZOS).convert("RGBA")
    a = np.asarray(small).copy()
    a[a[..., 3] < 8, 3] = 0
    a[a[..., 3] == 0, :3] = 255
    return Image.fromarray(a)


def outer_ring(alpha: np.ndarray, radius: float) -> np.ndarray:
    """Anti-aliased coverage of everything within `radius` px of the opaque area."""
    dist = ndimage.distance_transform_edt(~(alpha > 127))
    return np.clip(radius + 0.5 - dist, 0, 1)


def add_border(big: Image.Image, radius: float, color=WHITE) -> Image.Image:
    """Die-cut border of `color` under the art (keeps black outlines readable on dark UIs)."""
    ring = outer_ring(np.asarray(big.getchannel("A")), radius)
    base = np.zeros((*ring.shape, 4), dtype=np.uint8)
    base[..., :3] = color
    base[..., 3] = (ring * 255).astype(np.uint8)
    out = Image.fromarray(base)
    out.alpha_composite(big)
    return out


def place(art: Image.Image, canvas: tuple[int, int], box: tuple[int, int, int, int], border: float = 0,
          valign: str = "center", scale: float = 1.0) -> Image.Image:
    """Fit art (plus border) inside box=(x, y, w, h) of a transparent canvas; returns the 1x image."""
    W, H = canvas
    x, y, w, h = box
    big = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    bw, bh = (w - 2 * border) * S * scale, (h - 2 * border) * S * scale
    s = min(bw / art.width, bh / art.height)
    a = art.resize((max(1, round(art.width * s)), max(1, round(art.height * s))), Image.LANCZOS)
    px = x * S + (w * S - a.width) // 2
    py = {"center": y * S + (h * S - a.height) // 2, "bottom": (y + h - border) * S - a.height,
          "top": (y + border) * S}[valign]
    big.alpha_composite(a, (px, py))
    if border:
        big = add_border(big, border * S)
    return downsample(big, canvas)


def off_look(art: Image.Image) -> Image.Image:
    """Unselected state: same drawing in soft cool greys (black -> dark grey, yellow -> near white)."""
    a = np.asarray(art).astype(float)
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    v = 92 + lum * 0.62
    out = a.copy()
    out[..., 0], out[..., 1], out[..., 2] = v - 4, v, v + 8
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))


def silhouette(art: Image.Image, fill=(214, 221, 231), ring=(128, 139, 156), ring_px=LINE_W * 2.6) -> Image.Image:
    """Empty passcode slot: the head's silhouette in light grey with a grey rim."""
    pad = int(ring_px) + 2                               # room for the rim outside the trimmed art
    padded = Image.new("RGBA", (art.width + 2 * pad, art.height + 2 * pad), (0, 0, 0, 0))
    padded.paste(art, (pad, pad))
    alpha = np.asarray(padded.getchannel("A"))
    cov_in = alpha / 255.0
    cov_ring = outer_ring(alpha, ring_px)
    rgb = np.zeros((*alpha.shape, 3))
    rgb[:] = ring
    inner = cov_in[..., None]
    rgb = rgb * (1 - inner) + np.array(fill) * inner
    out = np.dstack([rgb, np.maximum(cov_ring, cov_in) * 255]).astype(np.uint8)
    return Image.fromarray(out)


def dash_tile(size: tuple[int, int], bg, fg, step: int = 32, dash: int = 11, width: int = 3,
              seed: int = 7, alpha_bg: int = 255) -> Image.Image:
    """Seamless tile of short 'stitch' dashes like the mascot's texture (drawn at S, returned at 1x)."""
    tw, th = size
    rnd = random.Random(seed)
    big = Image.new("RGBA", (tw * S, th * S), tuple(bg) + (alpha_bg,))
    d = ImageDraw.Draw(big)
    for gy in range(0, th, step):
        for gx in range(0, tw, step):
            cx = (gx + step / 2 + rnd.uniform(-step * 0.3, step * 0.3)) * S
            cy = (gy + step / 2 + rnd.uniform(-step * 0.3, step * 0.3)) * S
            ang = np.radians(rnd.choice([-35, -20, 20, 35, 60, -60]))
            dx, dy = np.cos(ang) * dash * S / 2, np.sin(ang) * dash * S / 2
            for ox in (-tw * S, 0, tw * S):                   # wrap around so the tile repeats cleanly
                for oy in (-th * S, 0, th * S):
                    d.line((cx - dx + ox, cy - dy + oy, cx + dx + ox, cy + dy + oy), fill=tuple(fg) + (255,),
                           width=width * S)
                    r = width * S / 2
                    for ex, ey in ((cx - dx + ox, cy - dy + oy), (cx + dx + ox, cy + dy + oy)):
                        d.ellipse((ex - r, ey - r, ex + r, ey + r), fill=tuple(fg) + (255,))
    return big.resize(size, Image.LANCZOS)


def patterned(size: tuple[int, int], bg, fg, **kw) -> Image.Image:
    tile = dash_tile((64, 64), bg, fg, **kw)
    out = Image.new("RGBA", size)
    for y in range(0, size[1], 64):
        for x in range(0, size[0], 64):
            out.paste(tile, (x, y))
    return out


def ledge_peek(peek: Image.Image, ledge_color) -> Image.Image:
    """Peeking mascot gripping a ledge (body hidden behind it, gloves over it)."""
    a = np.asarray(peek.getchannel("A"))
    h, w = a.shape
    cols = np.nonzero(a.max(axis=0) > 16)[0]
    body_bottom = int(np.nonzero(a[:, cols[len(cols) // 2]] > 16)[0].max())
    wall_h, pad = int(h * 0.15), int(w * 0.04)
    canvas = Image.new("RGBA", (w + 2 * pad, max(h, body_bottom + wall_h + 1)), (0, 0, 0, 0))
    ImageDraw.Draw(canvas).rounded_rectangle((0, body_bottom + 1, w + 2 * pad - 1, body_bottom + wall_h),
                                             radius=LINE_W * 2, fill=tuple(ledge_color) + (255,),
                                             outline=BLACK + (255,), width=LINE_W)
    canvas.alpha_composite(peek, (pad, 0))
    return canvas


def opaque(im: Image.Image) -> Image.Image:
    return im.convert("RGB")


# ---------- theme parts ----------

def menu_buttons(src: Path, out: Path):
    for name, (off_id, on_id) in TABS.items():
        on = trim(Image.open(src / f"tab-{name}.png").convert("RGBA"))
        off = off_look(on)
        for art, fid in ((off, off_id), (on, on_id)):
            # iOS < 26 and Android: 128x150, art in the band LINE's samples use (~y 20-120)
            place(art, (128, 150), (10, 20, 108, 100), border=3).save(out / f"i_{fid:02d}.png", optimize=True)
            # iOS 26+: 80x56, art centred in ~60x50
            place(art, (80, 56), (10, 3, 60, 50), border=2).save(out / f"i_{fid:02d}_g.png", optimize=True)


def passcode(src: Path, out: Path):
    for i, mood in enumerate(HEADS):
        on = trim(Image.open(src / f"head-{mood}.png").convert("RGBA"))
        off = silhouette(on)
        off_id, on_id = 12 + 2 * i, 13 + 2 * i
        for art, fid in ((off, off_id), (on, on_id)):
            border = 0 if art is off else 3
            place(art, (120, 120), (5, 5, 110, 110), border=border).save(out / f"i_{fid:02d}.png", optimize=True)
            place(art, (116, 116), (5, 5, 106, 106), border=border).save(out / f"a_{fid:02d}.png", optimize=True)


def profile(src: Path, out: Path):
    heads = {m: trim(Image.open(src / f"head-{m}.png").convert("RGBA")) for m in HEADS}
    for n in (240, 247):
        # individual: one big happy head on pale yellow
        bg = patterned((n, n), lighten(SECONDARY, 0.55), lighten(SECONDARY, 0.3), seed=3)
        bg.alpha_composite(place(heads["happy"], (n, n), (0, 0, n, n), border=4, scale=0.80))
        opaque(bg).save(out / ("i_20.png" if n == 240 else "a_20.png"), optimize=True)
        # group: three heads on brand blue, kept inside the circle the app crops to
        bg = patterned((n, n), BLUE, lighten(BLUE, 0.16), seed=5)
        side = int(n * 0.42)
        bg.alpha_composite(place(heads["wink"], (n, n), (int(n * 0.13), int(n * 0.16), side, side), border=3))
        bg.alpha_composite(place(heads["laughing"], (n, n), (n - int(n * 0.13) - side, int(n * 0.16), side, side), border=3))
        front = int(n * 0.50)
        bg.alpha_composite(place(heads["happy"], (n, n), ((n - front) // 2, n - front - int(n * 0.10), front, front), border=3))
        opaque(bg).save(out / ("i_21.png" if n == 240 else "a_21.png"), optimize=True)


def thumbnails(src: Path, out: Path):
    hero = trim(Image.open(src / "hero.png").convert("RGBA"))
    for name, (w, h) in {"ios_thumbnail.png": (200, 284), "android_thumbnail.png": (136, 202),
                         "store_thumbnail.png": (198, 278)}.items():
        bg = patterned((w, h), BLUE, lighten(BLUE, 0.16), seed=11)
        m = max(6, round(w * 0.07))
        bg.alpha_composite(place(hero, (w, h), (m, m, w - 2 * m, h - 2 * m), border=max(2, round(w / 60))))
        opaque(bg).save(out / name, optimize=True)


def menu_background(out: Path):
    """1472x150: top 20px transparent, 130px band that tiles seamlessly (1472 = 23 x 64)."""
    W, H, top = 1472, 150, 20
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    band = patterned((W, H - top), WHITE, lighten(BLUE, 0.85), seed=17)
    img.paste(band, (0, top))
    ImageDraw.Draw(img).rectangle((0, top, W - 1, top + 3), fill=BLUE + (255,))
    img.save(out / "i_11.png", optimize=True)


def chat_background(src: Path, out: Path):
    if (src / "peek.png").exists():
        art = ledge_peek(trim(Image.open(src / "peek.png").convert("RGBA")), WHITE)
    else:                                           # no peek pose: happy head sits at the bottom instead
        art = trim(Image.open(src / "head-happy.png").convert("RGBA"))
    # iOS shows the centre 640px in portrait; Android phones show ~1080px and the input box covers the bottom
    for name, (w, h), bottom_gap, mascot_w in (("i_22.png", (1482, 1334), 16, 300),
                                               ("a_22.png", (1300, 1300), 170, 420)):
        bg = patterned((w, h), lighten(BLUE, 0.84), lighten(BLUE, 0.93), seed=23)
        mh = round(art.height * mascot_w / art.width)
        box = ((w - mascot_w - 16) // 2, h - bottom_gap - mh - 16, mascot_w + 16, mh + 16)
        bg.alpha_composite(place(art, (w, h), box, border=4, valign="bottom"))
        opaque(bg).save(out / name, optimize=True)


def main(src: str, out: str):
    s, o = Path(src), Path(out)
    o.mkdir(parents=True, exist_ok=True)
    thumbnails(s, o)
    menu_buttons(s, o)
    menu_background(o)
    passcode(s, o)
    profile(s, o)
    chat_background(s, o)
    print(len(list(o.glob("*.png"))), "images ->", o)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--primary", default="#0088F8"); ap.add_argument("--secondary", default="#F8F808")
    a = ap.parse_args()
    BLUE, SECONDARY = hex_rgb(a.primary), hex_rgb(a.secondary)
    main(a.src, a.out)
