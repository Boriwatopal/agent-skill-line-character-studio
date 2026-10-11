# LINE Creators Market specs (verified 2026-09-25 / 2026-09-28)

LINE changes these with app updates. If anything below looks off, or the date is more than a few
months old, re-read the official pages (the built-in browser's get_page_text works; WebFetch misses the
detail tables):
- Stickers: https://creator.line.me/en/guideline/sticker/
- Theme overview: https://creator.line.me/en/guideline/theme/ — full sizes: https://creator.line.me/en/guideline/theme/detail/
- Emoji: https://creator.line.me/en/guideline/emoji/ — file names: https://creator.line.me/en/guideline/emoji/detail/

All submissions: PNG, RGB, transparent where noted, each file ≤ 1 MB, uploaded as ONE flat ZIP
(files at the ZIP root, no folders, lowercase names). Text fields: title ≤ 40 chars, description ≤ 160,
creator ≤ 50, copyright ≤ 50 (Thai/Asian characters count double).

## Stickers (static)
| Item | Size | Name |
|---|---|---|
| Stickers | max 370 × 320, **even** width and height, ~10 px margin around the art | 01.png … 40.png |
| Main image | 240 × 240 | main.png |
| Chat tab | 96 × 74 | tab.png |
- Set size must be exactly 8, 16, 24, 32 or 40. ZIP ≤ 60 MB. Transparent backgrounds.
- Rejection reasons that matter here: poor visibility (tiny full-length figures), sets lacking variety.
- Order matters: LINE shows stickers in number order — most-used reactions first.

## Theme (62 images)
| Part | Files | Size | Notes |
|---|---|---|---|
| Thumbnails | ios_thumbnail.png / android_thumbnail.png / store_thumbnail.png | 200×284 / 136×202 / 198×278 | background must NOT be transparent |
| Menu buttons (iOS < 26 + Android) | i_XX.png ×18 | 128 × 150 | art sits in ~x 10–118, y 20–120; app draws the tab label; badge 33×33 at top 49 / right 21 |
| Menu buttons (iOS 26+) | i_XX_g.png ×18 | 80 × 56 | art ~60×50 centred; must read on BOTH black and white bars |
| Menu background (optional) | i_11.png | 1472 × 150 | tiles seamlessly; 101–150 px tall for transparency; top 20 px transparent + 130 px art |
| Passcode | i_12…i_19 (iOS) / a_12…a_19 (Android) | 120×120 / 116×116 | 4 digits × OFF/ON (even = OFF, odd = ON) |
| Profile | i_20, i_21 / a_20, a_21 | 240×240 / 247×247 | 20 = individual, 21 = group; cropped to a circle in-app but tap shows the square — fill the square |
| Chat background (optional) | i_22 / a_22 | 1482×1334 / 1300×1300 (max) | ≤ 1 MB; centred + bottom-aligned; iOS portrait shows only the centre **640 px**; Android input box covers the bottom |

Menu-button file ids (OFF / ON):
Home 29/30 · Chats 03/04 · VOOM 33/34 · Shopping 35/36 · Calls 07/08 · News 25/26 · TODAY 31/32 · Wallet 27/28 · Apps 37/38

After upload the user picks a **colour skin** and a **chat background colour** in the web editor.
Tell them to set the background colour to the chat image's top edge colour (make_chatbg prints it),
so tall phones don't show a seam. LINE's own example uses character poses per tab (not function
icons) — either works; "no unifying theme among icons" and text-only icons get rejected.

## Emoji
| Item | Size | Name |
|---|---|---|
| Emoji (Regular set) | 180 × 180 | 001.png … 040.png |
| Chat tab | 96 × 74 | tab.png |
- 8–40 emoji, transparent, ≤ 1 MB each, ZIP < 20 MB.
- LINE recommends no margins, thick dark outlines, big distinct expressions (they appear tiny inline),
  few sparkles/motion lines, most-used first. Objects/scenery and name emoji are discouraged.

## Review risks worth warning the user about
- Parodies of famous films/logos (e.g. the E.T. bicycle crossing the moon is also Amblin's logo) may be
  rejected for a paid item even when the characters are original. Never draw the copyrighted character
  itself; offer a safe backup.
- No advertising, no corporate-logo-only designs, no references to other messaging services.
