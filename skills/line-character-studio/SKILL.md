---
name: line-character-studio
description: End-to-end studio for turning a logo or mascot into a LINE character product line with OpenAI GPT Image — asks the user for their OpenAI API key, designs the character in many action poses, then builds upload-ready LINE Creators Market packages for stickers (8–40, with or without captions), a full LINE theme (62 images incl. iOS 26 menu icons, passcode, profiles, chat background) and LINE emoji (8–40). Use this whenever the user wants to make a mascot/cartoon of their logo or brand, "create my character", character poses for presentations, or anything for LINE, such as "ทำสติกเกอร์ไลน์", "ทำธีมไลน์", "ทำอีโมจิไลน์", "LINE sticker", "LINE theme", "LINE emoji", "Creators Market", "sticker pack from my logo", "turn my mascot into stickers" — even if they only mention one of these products or never say "LINE" but clearly want chat stickers of their character.
---

# LINE Character Studio

Four stages, each usable on its own: **0 key → 1 character → 2 stickers / 3 theme / 4 emoji**.
Work in a folder the user chooses (default: the current project folder) — call it WORKDIR below.
Scripts live in `scripts/` next to this file (call it SK). All scripts are plain Python 3 + Pillow,
numpy, scipy. Exact LINE sizes, file names and review rules are in `references/line-specs.md` —
read it before building any LINE package.

Keep the user in the loop the way a designer would: show a preview image (SendUserFile, render)
after each stage, say what you chose, and offer the obvious next step. Users of this skill are often
non-technical; describe results in plain words, not file-format jargon.

## Step 0 — OpenAI API key

Check first: `python3 SK/scripts/set_api_key.py --check`.
If there is no working key, ask the user for one (they create it at
https://platform.openai.com/api-keys). Offer two ways, safest first:
1. They run `python3 SK/scripts/set_api_key.py` in their own terminal (hidden prompt; the key never
   enters the chat).
2. If they paste the key in chat, store it with
   `printf %s '<key>' | python3 SK/scripts/set_api_key.py --stdin` and never repeat it back.

The key is saved to `SK/.env` (chmod 600) and verified with a free call. Never write it into the
project folder, a prompt file, or a reply.

**Billing:** image generation costs money on the user's OpenAI account. If a run fails with
`HTTP 429 … insufficient_quota / credit_balance_exhausted`, stop and tell the user to add credits at
https://platform.openai.com/settings/organization/billing/ — you must not handle payments. Nothing is
lost; rerun the same command after they confirm. Mention rough scale before big batches
(each high-quality 1024² image is a paid call).

## Step 1 — Design the character

1. **Look at the logo/reference** (Read it). Note shape, face, clothing/accessories, outline style.
   Sample the exact palette:
   `python3 -c "from PIL import Image;from collections import Counter;im=Image.open('LOGO').convert('RGBA');print(Counter(tuple((c//8)*8 for c in p[:3]) for p in im.getdata() if p[3]>250).most_common(6))"`
   If the logo is text/abstract rather than a character, propose a mascot concept based on it and
   confirm with the user before spending credits.
2. **Write the base prompt**: copy `assets/base_character.txt` to WORKDIR and fill `{CHARACTER}`
   (every recognisable feature + hex colours), `{STYLE}` and `{PALETTE}`. See
   `assets/example_character_fill.md` for a worked example. The detail matters: whatever you don't
   pin down drifts between images.
3. **Pilot 2 poses first**, check them, then run the batch. Pose ideas for presentations/chat are in
   `assets/prompts_poses.json` (18 poses, presentation flow) and `assets/prompts_chat_emotions.json`
   (sorry/love/laughing/good night). Adapt props/colours to the character.
   ```bash
   python3 SK/scripts/gen_images.py --prompts poses.json --out WORKDIR/raw --image LOGO \
     --base "$(cat WORKDIR/base_character.txt)" --size 1024x1024 --quality high \
     --background transparent --workers 6
   ```
   Run big batches in the background (`run_in_background`) — ~2–3 min per image, 6 in parallel.
4. **Clean every output** before use:
   `python3 SK/scripts/clean_png.py WORKDIR/poses WORKDIR/raw/*.png`
   (gpt-image transparent PNGs leave the character ~98 % opaque and a coloured "glow" hidden under
   transparent pixels; this snaps alpha, whitens hidden RGB and trims margins. `--cut-bottom ROW`
   trims flush for peek-style poses.)
5. **Review**: `python3 SK/scripts/contact_sheet.py WORKDIR/poses WORKDIR/overview.png`, then look at
   poses at larger size (hands, props, stray text). Re-run only failed poses. The "glow" you may see
   when Reading a transparent PNG is a viewer artefact — composite on white/navy to judge.

Keep one **peek pose** (upper body rising over a straight bottom edge, gloves gripping it) — the
sticker ledge, theme chat background and tab icon reuse it.

## Step 2 — LINE stickers

Ask (once, together): **language of captions** (or no text — many users prefer no text), and **set
size** (8/16/24/32/40; propose reusing existing poses + a few new chat emotions to reach the size).
Order by use: hello, thanks, OK, sorry, laugh, love… first.

1. Write a spec JSON (see `assets/sticker_spec_example.json`): per sticker `n`, `src`, optional
   `lines` (line-break variants; the layout search picks the best), `mode`:
   `sign` (writes the caption onto a blank sign the mascot holds), `wall` (peek pose gripping a
   ledge), `banner` (caption written on the ledge), optional `prefer: top|bottom|left|right`.
   Add `{"kind":"main",…}` and `{"kind":"tab",…}` entries. No `lines` = no-text sticker.
2. `python3 SK/scripts/make_stickers.py spec.json WORKDIR/stickers_build` (edit `FONT`/colours at the
   top of the script for the brand; default Gill Sans UltraBold, brand-blue fill, black outline, 5 px
   white die-cut border for dark mode).
3. `python3 SK/scripts/finalize_line.py WORKDIR/stickers_build "WORKDIR/LINE Stickers" WORKDIR/LINE-stickers-upload.zip`
   — trims to content + 10 px, even sizes, validates every rule, writes the flat ZIP.
4. Preview on light and dark chat colours:
   `python3 SK/scripts/sticker_preview.py "WORKDIR/LINE Stickers" preview.png light 0.75` (and `dark`).

**Captions are always rendered in code, never by the image model** (it misspells, especially Thai).
Thai captions: Pillow here has no raqm, so Thai vowels/tone marks mis-stack — render Thai lines with
`pango-view` (HarfBuzz) to a mask first, or check `features.check('raqm')`.

## Step 3 — LINE theme

1. Generate the art (adapt `assets/prompts_theme.json`): 9 menu-tab busts `tab-home/chats/voom/
   shopping/calls/news/today/wallet/apps` (mascot holding the tab's prop) + 4 heads
   `head-happy/wink/surprised/laughing`. Head/bust prompts must say "no body, no legs" or the model
   sometimes draws a tiny full figure.
2. Clean into one folder `WORKDIR/theme_src` and add `hero.png` (a full-body pose for the
   thumbnails) and `peek.png` (optional).
3. `python3 SK/scripts/make_theme.py WORKDIR/theme_src "WORKDIR/LINE Theme" --primary "#HEX" --secondary "#HEX"`
   builds all 62 images: selected tab = full colour, unselected = soft greys; passcode ON = heads,
   OFF = grey silhouettes; profiles; menu background; thumbnails; a default chat background.
4. `python3 SK/scripts/finalize_theme.py "WORKDIR/LINE Theme" WORKDIR/LINE-theme-upload.zip` validates
   names/sizes/opacity/1 MB and zips; `python3 SK/scripts/theme_preview.py "WORKDIR/LINE Theme" preview.png "Name"`
   shows a phone mockup, menu bars (old iOS/Android + iOS 26 light & dark), passcode and profiles.

**Custom chat background scene** (e.g. a movie-poster parody): generate square scenes with
`--base "$(cat base_scene.txt)"` (fill its placeholders) and `--background opaque`, then
`python3 SK/scripts/make_chatbg.py OUTDIR compare.png scene1.png scene2.png …` — it fits the subject
into the iOS portrait centre column (640 px), mirrors the side edges, quantises under 1 MB, and prints
the top-edge colour to give the user for LINE's background-colour setting. Keep the previous
`i_22/a_22` as a backup, and read the review-risk notes in `references/line-specs.md` for parodies.

## Step 4 — LINE emoji

1. Generate 8–40 expressions (adapt `assets/prompts_emoji.json`; reuse the theme heads). Emoji are
   seen tiny inline: head close-ups, huge expressions, few extras.
2. Clean into `WORKDIR/emoji_src` (files named `head-*.png` / `emo-*.png`).
3. `python3 SK/scripts/make_emoji.py WORKDIR/emoji_src "WORKDIR/LINE Emoji" WORKDIR/LINE-emoji-upload.zip preview.png`
   — 180×180 no-margin art with a thin white edge, most-used first (edit `ORDER` to change), tab.png,
   validated flat ZIP, and a preview on light/dark plus an inline-message mock.
4. Check every emoji at small size; regenerate any that reads as a tiny figure or unclear face.

## Delivering

For each product give the user: the upload ZIP, the image folder, one preview (sent with
SendUserFile), a short table of what's inside, which LINE rules were checked, and the submission
steps (Creators Market → My Page → New Submission → type → text fields → upload ZIP; themes also need
colour skin + chat background colour). Keep earlier versions instead of deleting them when the user
changes direction (e.g. rename to "… (with text)"), and save hi-res source art in the project folder —
the scratch copies disappear.
