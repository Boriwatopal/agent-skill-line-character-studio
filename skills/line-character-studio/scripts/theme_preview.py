#!/usr/bin/env python3
"""One overview sheet of a LINE theme: store thumbnails, a chat-room phone mockup, menu bars
(older iOS/Android and iOS 26 on light + dark), every menu icon OFF/ON, passcode, profiles.

Usage: theme_preview.py THEME_DIR OUT.png [CHARACTER_NAME]
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

TABS = [("Home", 29, 30), ("Chats", 3, 4), ("VOOM", 33, 34), ("Shopping", 35, 36), ("Calls", 7, 8),
        ("News", 25, 26), ("TODAY", 31, 32), ("Wallet", 27, 28), ("Apps", 37, 38)]
BG, INK, MUTED = (243, 245, 249), (22, 26, 34), (110, 118, 132)


def F(size, bold=False):
    return ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", size, index=1 if bold else 0)


def img(d, name):
    return Image.open(d / name).convert("RGBA")


def paste(sheet, im, xy):
    sheet.paste(im, xy, im)


def rounded_mask(size, r):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), r, fill=255)
    return m


def chat_mockup(d: Path, name: str = "Chat") -> Image.Image:
    """iPhone-ish chat room: bottom-aligned chat background, bubbles, input bar."""
    W, H = 360, 740
    phone = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    bg = img(d, "i_22.png")
    # iOS portrait shows the centre 640px of the image, bottom-aligned above the input field
    c = bg.crop(((bg.width - 640) // 2, 0, (bg.width + 640) // 2, bg.height)).resize((W, round(1334 * W / 640)))
    top, input_h = 64, 56
    area_h = H - top - input_h
    phone.paste(c.crop((0, c.height - area_h, W, c.height)), (0, top))
    dr = ImageDraw.Draw(phone)
    dr.rectangle((0, 0, W, top), fill=(255, 255, 255))
    dr.text((W // 2, 40), name, font=F(17, True), fill=INK, anchor="mm")
    dr.line((0, top, W, top), fill=(225, 228, 234))
    y = top + 24
    for text, mine in [("Hi! Ready for class?", False), ("Yes! See you there", True),
                       ("Bring your laptop", False), ("OK!", True)]:
        f = F(15)
        tw = dr.textlength(text, font=f)
        bw, bh = tw + 28, 38
        x = W - bw - 14 if mine else 14
        dr.rounded_rectangle((x, y, x + bw, y + bh), 18, fill=(248, 240, 80) if mine else (255, 255, 255),
                             outline=(0, 0, 0) if mine else None, width=1)
        dr.text((x + 14, y + bh / 2), text, font=f, fill=INK, anchor="lm")
        y += bh + 12
    dr.rectangle((0, H - input_h, W, H), fill=(255, 255, 255))
    dr.rounded_rectangle((48, H - input_h + 10, W - 48, H - 10), 18, fill=(240, 242, 246))
    phone.putalpha(rounded_mask((W, H), 36))
    frame = Image.new("RGBA", (W + 16, H + 16), (0, 0, 0, 0))
    ImageDraw.Draw(frame).rounded_rectangle((0, 0, W + 15, H + 15), 44, fill=(20, 22, 28))
    frame.alpha_composite(phone, (8, 8))
    return frame


def menu_bar_legacy(d: Path, selected: int = 0) -> Image.Image:
    """Older iOS / Android bar: menu background + 128x150 buttons (app draws the labels)."""
    tabs = [TABS[i] for i in (0, 1, 2, 6, 7)]
    W, H = 5 * 128, 150 + 30
    bar = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    mb = img(d, "i_11.png")
    bar.paste(mb.crop((0, 0, W, 150)), (0, 0))
    ImageDraw.Draw(bar).rectangle((0, 150, W, H), fill=(255, 255, 255))
    dr = ImageDraw.Draw(bar)
    for k, (label, off, on) in enumerate(tabs):
        icon = img(d, f"i_{(on if k == selected else off):02d}.png")
        bar.alpha_composite(icon, (k * 128, 0))
        dr.text((k * 128 + 64, 150), label, font=F(20, k == selected), anchor="mm",
                fill=(0, 136, 248) if k == selected else MUTED)
    return bar


def menu_bar_ios26(d: Path, dark: bool, selected: int = 0) -> Image.Image:
    tabs = [TABS[i] for i in (0, 1, 2, 6, 7)]
    s = 1.6                                             # enlarged so it's readable, still fits the sheet
    W, H = int(5 * 80 * s + 40), int(56 * s + 44)
    bar = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fill = (28, 28, 32, 235) if dark else (255, 255, 255, 235)
    ImageDraw.Draw(bar).rounded_rectangle((0, 0, W - 1, H - 1), H // 2, fill=fill)
    dr = ImageDraw.Draw(bar)
    for k, (label, off, on) in enumerate(tabs):
        icon = img(d, f"i_{(on if k == selected else off):02d}_g.png").resize((int(80 * s), int(56 * s)), Image.LANCZOS)
        bar.alpha_composite(icon, (int(20 + k * 80 * s), 4))
        dr.text((int(20 + k * 80 * s + 40 * s), int(56 * s + 20)), label, font=F(15, k == selected), anchor="mm",
                fill=(0, 136, 248) if k == selected else ((200, 200, 205) if dark else MUTED))
    return bar


def main(theme_dir: str, out: str, name: str = "My character"):
    d = Path(theme_dir)
    sheet = Image.new("RGBA", (1880, 1330), BG + (255,))
    dr = ImageDraw.Draw(sheet)
    h1, h2 = F(26, True), F(17, True)

    def title(x, y, t):
        dr.text((x, y), t, font=h2, fill=INK)

    dr.text((40, 28), f"{name} — LINE theme", font=h1, fill=INK)
    # left column: phone mockup
    paste(sheet, chat_mockup(d, name), (40, 90))
    title(40, 862, "Chat room (iOS portrait, chat background i_22)")
    # store thumbnails
    x0 = 470
    title(x0, 90, "Store / shop thumbnails")
    x = x0
    for n in ("ios_thumbnail.png", "store_thumbnail.png", "android_thumbnail.png"):
        t = img(d, n)
        paste(sheet, t, (x, 124))
        x += t.width + 24
    # profiles (square + circle crop)
    title(x0 + 600, 90, "Profile images (square + in-app circle)")
    px = x0 + 600
    for n in ("i_20.png", "i_21.png"):
        p = img(d, n).resize((150, 150), Image.LANCZOS)
        paste(sheet, p, (px, 124))
        circ = p.copy()
        m = Image.new("L", (150, 150), 0)
        ImageDraw.Draw(m).ellipse((0, 0, 149, 149), fill=255)
        circ.putalpha(m)
        paste(sheet, circ, (px, 290))
        px += 180
    # passcode
    title(x0 + 960, 90, "Passcode OFF / ON (4 digits)")
    for i in range(4):
        off = img(d, f"i_{12 + 2 * i}.png").resize((84, 84), Image.LANCZOS)
        on = img(d, f"i_{13 + 2 * i}.png").resize((84, 84), Image.LANCZOS)
        paste(sheet, off, (x0 + 960 + i * 92, 124))
        paste(sheet, on, (x0 + 960 + i * 92, 216))
    # menu bars
    title(x0, 452, "Menu bar — older iOS & Android (menu background i_11 + 128x150 buttons)")
    paste(sheet, menu_bar_legacy(d), (x0, 484))
    title(x0 + 690, 452, "Menu bar — iOS 26 (80x56), light and dark")
    paste(sheet, menu_bar_ios26(d, dark=False), (x0 + 690, 484))
    paste(sheet, menu_bar_ios26(d, dark=True), (x0 + 690, 650))
    # all icons OFF / ON
    title(x0, 850, "All 9 menu buttons — OFF (top) / ON (bottom)")
    for k, (label, off, on) in enumerate(TABS):
        cx = x0 + k * 150
        for row, fid in enumerate((off, on)):
            ic = img(d, f"i_{fid:02d}.png")
            tile = Image.new("RGBA", (128, 150), (255, 255, 255, 255))
            tile.alpha_composite(ic)
            paste(sheet, tile, (cx, 884 + row * 170))
        dr.text((cx + 64, 1214), label, font=F(15), fill=MUTED, anchor="mm")
    sheet.convert("RGB").save(out, optimize=True)
    print(out, sheet.size)


if __name__ == "__main__":
    main(*sys.argv[1:4])
