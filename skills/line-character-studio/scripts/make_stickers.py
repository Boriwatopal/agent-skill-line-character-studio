#!/usr/bin/env python3
"""Compose LINE stickers (370x320, transparent PNG) from mascot art + English captions.

Each sticker: mascot scaled as large as possible, caption placed where it covers the least
of the character (legs count less than head/body), then a white die-cut border around both
so the black outlines stay visible on LINE's dark theme. Rendered at 3x and downsampled.

Usage: make_stickers.py SPEC.json OUT_DIR
SPEC entries: {"n": 1, "src": "path.png", "lines": [["Hello!"]], "mode": "caption" | "sign" | "wall"}
  lines = list of line-break variants to try, e.g. [["Check this out!"], ["Check", "this out!"]]
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

S = 3                                  # supersampling factor
W, H = 370, 320                        # LINE max sticker size (both even)
MARGIN = 12                            # LINE wants ~10px clear; +2 absorbs downsampling blur (trimmed to 10 later)
BORDER = 5                             # white die-cut border (1x px)
TEXT_BLACK = 3                         # caption black outline (1x px)
TEXT_WHITE = TEXT_BLACK + BORDER       # caption white ring ends where the die-cut border ends
FONT = ("/System/Library/Fonts/Supplemental/GillSans.ttc", 6)   # Gill Sans UltraBold
FONT_SIZES = [66, 60, 56, 52, 48]      # narrow range keeps captions consistent across the set
SCALES = [1.0, 0.94, 0.88, 0.82, 0.76, 0.70]
BLUE, BLACK, WHITE = (0, 136, 248), (0, 0, 0), (255, 255, 255)
LINE_W = 9                             # outline weight of the art at ~1024px source scale

# usable box for mascot/caption at 1x (inside margin + border)
UX0 = UY0 = MARGIN + BORDER
UX1, UY1 = W - MARGIN - BORDER, H - MARGIN - BORDER
UW, UH = UX1 - UX0, UY1 - UY0


def font(px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT[0], px, index=FONT[1])


def text_box(text: str, f, stroke: int, spacing: int) -> tuple[int, int, int, int]:
    """Integer multiline bbox (Pillow 11 returns floats)."""
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    l, t, r, b = probe.multiline_textbbox((0, 0), text, font=f, stroke_width=stroke, spacing=spacing, align="center")
    return math.floor(l), math.floor(t), math.ceil(r), math.ceil(b)


def caption(lines: list[str], fs: int, scale: int) -> tuple[Image.Image, Image.Image]:
    """Blue caption with black outline + white ring; returns (full, core) cropped identically.

    The core (fill + black outline) drives the die-cut border; the full image carries its own
    white ring so the caption stays legible where it overlaps the mascot."""
    f = font(fs * scale)
    text = "\n".join(lines)
    sw, sb = TEXT_WHITE * scale, TEXT_BLACK * scale
    spacing = -int(0.10 * fs * scale)
    l, t, r, b = text_box(text, f, sw, spacing)
    size = (r - l + 4 * scale, b - t + 4 * scale)
    xy = (2 * scale - l, 2 * scale - t)
    core = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(core).multiline_text(xy, text, font=f, fill=BLUE, stroke_width=sb, stroke_fill=BLACK,
                                        spacing=spacing, align="center")
    full = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(full).multiline_text(xy, text, font=f, fill=WHITE, stroke_width=sw, stroke_fill=WHITE,
                                        spacing=spacing, align="center")
    full.alpha_composite(core)
    box = full.getbbox()
    return full.crop(box), core.crop(box)


def integral(a: np.ndarray) -> np.ndarray:
    return np.pad(a.cumsum(0).cumsum(1), ((1, 0), (1, 0)))


def allowed(prefer: str | None, xs_, ys_, tw, th) -> np.ndarray:
    """Mask of caption positions matching a forced side (top/bottom/left/right), or all."""
    ok = np.ones((len(ys_), len(xs_)), dtype=bool)
    if prefer == "top":
        ok &= (ys_ <= UY0 + 0.2 * UH)[:, None]
    elif prefer == "bottom":
        ok &= (ys_ + th >= UY1 - 0.2 * UH)[:, None]
    elif prefer == "left":
        ok &= (xs_ <= UX0 + 0.2 * UW)[None, :]
    elif prefer == "right":
        ok &= (xs_ + tw >= UX1 - 0.2 * UW)[None, :]
    return ok


def best_layout(mascot: Image.Image, variants: list[list[str]], prefer: str | None = None,
                sizes: list[int] = FONT_SIZES):
    """Search mascot scale/position + caption size/position; return the best placement at 1x.

    Falls back to smaller caption sizes only when no variant fits at the normal sizes."""
    best = _search(mascot, variants, prefer, sizes)
    if best is None and sizes is FONT_SIZES:
        best = _search(mascot, variants, prefer, [44, 40, 36])
    if best is None:
        raise ValueError(f"caption {variants} does not fit")
    return best


def _search(mascot: Image.Image, variants: list[list[str]], prefer: str | None, sizes: list[int]):
    mw0, mh0 = mascot.size
    s_max = min(UW / mw0, UH / mh0)
    alpha = np.asarray(mascot.getchannel("A"))
    best = None
    for rel in SCALES:
        s = s_max * rel
        mw, mh = max(1, round(mw0 * s)), max(1, round(mh0 * s))
        m = np.asarray(Image.fromarray(alpha).resize((mw, mh), Image.BILINEAR)) > 64
        weight = np.where(np.arange(mh)[:, None] < 0.72 * mh, 1.0, 0.35)   # legs/shoes matter less
        mweighted = m * weight
        xs = sorted({UX0, UX1 - mw, *range(UX0, UX1 - mw + 1, 10)})
        ys = sorted({UY0, UY1 - mh, (UY0 + UY1 - mh) // 2})
        for mx in xs:
            for my in ys:
                canvas = np.zeros((H, W))
                canvas[my:my + mh, mx:mx + mw] = mweighted
                I = integral(canvas)
                for lines in variants:
                    for fs in sizes:
                        cap = caption_size(tuple(lines), fs)
                        tw, th = cap
                        if tw > UW or th > UH:
                            continue
                        # overlap for every caption position inside the usable box (vectorised)
                        ys_ = np.arange(UY0, UY1 - th + 1)
                        xs_ = np.arange(UX0, UX1 - tw + 1)
                        ov = (I[ys_[:, None] + th, xs_[None, :] + tw] - I[ys_[:, None], xs_[None, :] + tw]
                              - I[ys_[:, None] + th, xs_[None, :]] + I[ys_[:, None], xs_[None, :]])
                        frac = ov / (tw * th)
                        # mild pull toward the canvas centre so captions don't hide in corners
                        cy = (ys_[:, None] + th / 2 - H / 2) / H
                        cx = (xs_[None, :] + tw / 2 - W / 2) / W
                        score = rel + 0.9 * fs / FONT_SIZES[0] - 2.5 * frac - 0.12 * np.hypot(cx, cy)
                        score = np.where(allowed(prefer, xs_, ys_, tw, th), score, -np.inf)
                        k = np.unravel_index(np.argmax(score), score.shape)
                        sc = score[k]
                        if best is None or sc > best[0]:
                            best = (sc, s, mx, my, mw, mh, lines, fs, int(xs_[k[1]]), int(ys_[k[0]]), tw, th)
    return best


_cap_cache: dict = {}


def caption_size(lines: tuple, fs: int):
    key = (lines, fs)
    if key not in _cap_cache:
        _cap_cache[key] = caption(list(lines), fs, 1)[0].size
    return _cap_cache[key]


def die_cut(alpha: np.ndarray, radius: float) -> Image.Image:
    """White border of `radius` px around everything opaque in `alpha` (anti-aliased)."""
    a = alpha > 127
    dist = ndimage.distance_transform_edt(~a)
    border = np.clip(radius + 0.5 - dist, 0, 1)
    out = np.zeros((*a.shape, 4), dtype=np.uint8)
    out[..., :3] = 255
    out[..., 3] = (border * 255).astype(np.uint8)
    return Image.fromarray(out)


def finish(art: Image.Image, cut_alpha: np.ndarray, size: tuple[int, int], radius: float) -> Image.Image:
    """Die-cut border (from cut_alpha) under the art, then downsample with premultiplied alpha."""
    base = die_cut(cut_alpha, radius)
    base.alpha_composite(art)
    small = base.convert("RGBa").resize(size, Image.LANCZOS).convert("RGBA")
    arr = np.asarray(small).copy()
    arr[arr[..., 3] < 8, 3] = 0              # drop invisible resampling haze so margins are honest
    arr[arr[..., 3] == 0, :3] = 255
    return Image.fromarray(arr)


def fit_only(mascot: Image.Image, size: tuple[int, int], margin: int, border: int) -> Image.Image:
    """Mascot alone, as large as fits, centred, with die-cut border (used for main/tab images)."""
    w, h = size
    uw, uh = w - 2 * (margin + border), h - 2 * (margin + border)
    s = min(uw / mascot.width, uh / mascot.height)
    mw, mh = round(mascot.width * s * S), round(mascot.height * s * S)
    big = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    big.alpha_composite(mascot.resize((mw, mh), Image.LANCZOS), ((w * S - mw) // 2, (h * S - mh) // 2))
    return finish(big, np.asarray(big.getchannel("A")), size, border * S)


def center_group(boxes):
    """Offset that centres the union of boxes inside the usable area."""
    x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
    x1 = max(b[2] for b in boxes); y1 = max(b[3] for b in boxes)
    return (UX0 + UX1) // 2 - (x0 + x1) // 2, (UY0 + UY1) // 2 - (y0 + y1) // 2


def compose(mascot: Image.Image, variants, prefer: str | None = None) -> tuple[Image.Image, dict]:
    if not variants:
        return fit_only(mascot, (W, H), MARGIN, BORDER), {"caption": "on the art"}
    sc, s, mx, my, mw, mh, lines, fs, tx, ty, tw, th = best_layout(mascot, variants, prefer)
    dx, dy = center_group([(mx, my, mx + mw, my + mh), (tx, ty, tx + tw, ty + th)])
    mx, my, tx, ty = mx + dx, my + dy, tx + dx, ty + dy
    art = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    art.alpha_composite(mascot.resize((mw * S, mh * S), Image.LANCZOS), (mx * S, my * S))
    cut = np.asarray(art.getchannel("A")).copy()
    full, core = caption(lines, fs, S)
    # centre the 3x caption on its 1x slot (sizes differ by rounding only), clamped to the canvas
    cx = min(max(0, tx * S + (tw * S - full.width) // 2), W * S - full.width)
    cy = min(max(0, ty * S + (th * S - full.height) // 2), H * S - full.height)
    art.alpha_composite(full, (cx, cy))
    core_a = np.asarray(core.getchannel("A"))
    region = cut[cy:cy + core.height, cx:cx + core.width]
    np.maximum(region, core_a, out=region)
    return finish(art, cut, (W, H), BORDER * S), {"lines": lines, "fs": fs, "mascot_h": mh, "score": round(float(sc), 3)}


def add_sign_text(mascot: Image.Image, lines: list[str]) -> Image.Image:
    """Write the caption onto the blank sign the mascot is holding, following the sign's tilt."""
    a = np.asarray(mascot).astype(int)
    white = (a[..., 3] > 200) & (a[..., :3].min(axis=2) > 225)
    white[int(a.shape[0] * 0.45):] = False                      # the sign is in the upper part
    lab, n = ndimage.label(white)
    sizes = ndimage.sum(white, lab, range(1, n + 1))
    region = lab == (int(np.argmax(sizes)) + 1)
    ys, xs = np.nonzero(region)
    cy, cx = ys.mean(), xs.mean()
    cov = np.cov(np.vstack([xs - cx, ys - cy]))
    evals, evecs = np.linalg.eigh(cov)
    major = evecs[:, np.argmax(evals)]
    angle = np.degrees(np.arctan2(major[1], major[0]))
    if angle > 90: angle -= 180
    if angle < -90: angle += 180
    # extent along/across the major axis
    u = (xs - cx) * major[0] + (ys - cy) * major[1]
    v = -(xs - cx) * major[1] + (ys - cy) * major[0]
    box_w, box_h = (u.max() - u.min()) * 0.9, (v.max() - v.min()) * 0.8
    fs = 200
    while fs > 10:
        f = font(fs)
        l, t, r, b = text_box("\n".join(lines), f, 0, -int(0.08 * fs))
        if r - l <= box_w and b - t <= box_h:
            break
        fs -= 2
    txt = Image.new("RGBA", (r - l + 20, b - t + 20), (0, 0, 0, 0))
    ImageDraw.Draw(txt).multiline_text((10 - l, 10 - t), "\n".join(lines), font=f, fill=BLUE,
                                       spacing=-int(0.08 * fs), align="center")
    txt = txt.rotate(-angle, resample=Image.BICUBIC, expand=True)
    out = mascot.copy()
    out.alpha_composite(txt, (int(cx - txt.width / 2), int(cy - txt.height / 2)))
    return out


def add_wall(mascot: Image.Image, lines: list[str] | None = None) -> Image.Image:
    """Put a blue ledge under a peeking mascot: body sits behind it, gloves grip over it.

    With `lines`, the ledge becomes a taller banner with the caption written on it in white."""
    a = np.asarray(mascot.getchannel("A"))
    h, w = a.shape
    cols = np.nonzero(a.max(axis=0) > 16)[0]
    mid = cols[len(cols) // 2]
    body_bottom = int(np.nonzero(a[:, mid] > 16)[0].max())      # the flat cut of the body
    wall_h = int(h * (0.55 if lines else 0.15))
    pad = int(w * 0.04)
    cw = w + 2 * pad
    canvas = Image.new("RGBA", (cw, max(h, body_bottom + wall_h + 1)), (0, 0, 0, 0))
    ImageDraw.Draw(canvas).rounded_rectangle(
        (0, body_bottom + 1, cw - 1, body_bottom + wall_h),
        radius=LINE_W * 2, fill=BLUE + (255,), outline=BLACK + (255,), width=LINE_W)
    canvas.alpha_composite(mascot, (pad, 0))
    if lines:
        glove_bottom = int(np.nonzero(a.max(axis=1) > 16)[0].max())  # gloves hang over the top of the banner
        top, bottom = glove_bottom + LINE_W, body_bottom + wall_h - 2 * LINE_W
        box_w, box_h = cw * 0.86, (bottom - top) * 0.92
        stroke = LINE_W
        fs = 400
        while fs > 10:
            f = font(fs)
            l, t, r, b = text_box("\n".join(lines), f, stroke, -int(0.08 * fs))
            if r - l <= box_w and b - t <= box_h:
                break
            fs -= 4
        d = ImageDraw.Draw(canvas)
        d.multiline_text((cw / 2 - (l + r) / 2, (top + bottom) / 2 - (t + b) / 2), "\n".join(lines), font=f,
                         fill=WHITE + (255,), stroke_width=stroke, stroke_fill=BLACK + (255,),
                         spacing=-int(0.08 * fs), align="center")
    return canvas


def trim(im: Image.Image) -> Image.Image:
    return im.crop(im.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox())


def load_art(e: dict) -> tuple[Image.Image, list]:
    m = trim(Image.open(e["src"]).convert("RGBA"))
    mode = e.get("mode", "caption")
    variants = e.get("lines", [])
    if mode == "sign":
        m, variants = add_sign_text(m, variants[0]), []
    elif mode == "wall":
        m = add_wall(m)
    elif mode == "banner":
        m, variants = add_wall(m, variants[0]), []
    return m, variants


def margins(img: Image.Image) -> tuple[int, int, int, int]:
    l, t, r, b = img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    return l, t, img.width - r, img.height - b


def main(spec_path: str, out_dir: str, only: set[int] | None = None):
    spec = json.loads(Path(spec_path).read_text())
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for e in spec:
        if "n" in e and only and e["n"] not in only:
            continue
        m, variants = load_art(e)
        if e.get("kind") == "main":
            img, name = fit_only(m, (240, 240), 6, 4), "main.png"
        elif e.get("kind") == "tab":
            img, name = fit_only(m, (96, 74), 2, 2), "tab.png"
        else:
            img, info = compose(m, variants, e.get("prefer"))
            name = f"{e['n']:02d}.png"
        img.save(out / name, optimize=True)
        print(name, img.size, "margins l/t/r/b:", margins(img), "" if e.get("kind") else info)


if __name__ == "__main__":
    only = {int(x) for x in sys.argv[3].split(",")} if len(sys.argv) > 3 else None
    main(sys.argv[1], sys.argv[2], only)


