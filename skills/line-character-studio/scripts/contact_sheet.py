#!/usr/bin/env python3
"""Lay the cleaned mascot PNGs out on one 1920x1080 overview sheet with labels.

Usage: contact_sheet.py IMG_DIR OUT.png
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

LABELS = {
    "01-wave-hello": ("Wave hello", "Opening slide"),
    "02-wai-greeting": ("Thai wai", "Welcome / thank you"),
    "03-holding-sign": ("Blank sign", "Title / key message"),
    "04-agenda-checklist": ("Checklist", "Agenda / steps"),
    "05-thinking": ("Thinking", "Problem / question"),
    "06-idea-lightbulb": ("Big idea", "Insight / solution"),
    "07-magnifying-glass": ("Magnifier", "Research / analysis"),
    "08-ai-robot-highfive": ("Robot high-five", "AI topics"),
    "09-megaphone": ("Megaphone", "Announcement / CTA"),
    "10-rocket-launch": ("Rocket", "Growth / launch"),
    "11-goal-flag": ("Summit flag", "Goals / milestones"),
    "12-trophy": ("Trophy", "Results / wins"),
    "13-celebrate-jump": ("Celebrate", "Success"),
    "14-coffee-break": ("Coffee break", "Break slide"),
    "15-qa-microphone": ("Microphone", "Q&A"),
    "16-peek-from-bottom": ("Peek", "Slide-edge decoration"),
    "17-thumbs-up": ("Thumbs up", "Recap / agreement"),
    "18-point-right": ("Point right", "Point at content"),
    "19-sorry": ("Sorry", "Apology / oops"),
    "20-love": ("Love", "Appreciation / fans"),
    "21-laughing": ("Laughing", "Fun moment"),
    "22-good-night": ("Good night", "Wrap-up / rest"),
}

COLS, CELL_W, CELL_H, IMG_BOX, TOP = 6, 320, 350, 270, 15
BG, CARD, INK, MUTED = (244, 246, 250), (255, 255, 255), (20, 24, 33), (104, 112, 128)


def font(size, bold=False):
    for path, idx in (("/System/Library/Fonts/HelveticaNeue.ttc", 1 if bold else 0),
                      ("/System/Library/Fonts/Helvetica.ttc", 1 if bold else 0)):
        try:
            return ImageFont.truetype(path, size, index=idx)
        except OSError:
            continue
    return ImageFont.load_default()


def main(img_dir: Path, out: Path):
    files = sorted(p for p in img_dir.glob("[0-9][0-9]-*.png"))
    rows = (len(files) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * CELL_W, TOP * 2 + rows * CELL_H), BG)
    d = ImageDraw.Draw(sheet)
    f_name, f_use = font(22, bold=True), font(17)

    for i, p in enumerate(files):
        cx, cy = (i % COLS) * CELL_W, TOP + (i // COLS) * CELL_H
        d.rounded_rectangle((cx + 10, cy + 8, cx + CELL_W - 10, cy + CELL_H - 8), 18, fill=CARD)
        im = Image.open(p).convert("RGBA")
        im.thumbnail((IMG_BOX - 20, IMG_BOX - 20), Image.LANCZOS)
        sheet.paste(im, (cx + (CELL_W - im.width) // 2, cy + 18 + (IMG_BOX - 20 - im.height) // 2), im)
        name, use = LABELS.get(p.stem, (p.stem, ""))
        num = p.stem.split("-")[0]
        d.text((cx + CELL_W // 2, cy + IMG_BOX + 22), f"{num}  {name}", font=f_name, fill=INK, anchor="mm")
        d.text((cx + CELL_W // 2, cy + IMG_BOX + 50), use, font=f_use, fill=MUTED, anchor="mm")

    sheet.save(out, optimize=True)
    print(f"{out} ({sheet.width}x{sheet.height}, {len(files)} images)")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
