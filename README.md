# LINE Character Studio - Agent Skill

A Claude skill that turns a logo or mascot into a full **LINE character product line** with OpenAI GPT Image: it designs the character in many action poses, then builds upload-ready [LINE Creators Market](https://creator.line.me) packages for **stickers**, a complete **theme** and **emoji**, each as a validated ZIP with a preview.

Built while making the mascot, stickers, theme and emoji for [hundredable.com](https://hundredable.com) — the workflow and scripts are general; the hundredable artwork is not included.

## Install

**Claude Code (CLI / desktop app)** — clone the skill into your skills folder:

```bash
git clone https://github.com/Boriwatopal/agent-skill-line-character-studio.git /tmp/lcs && \
cp -R /tmp/lcs/skills/line-character-studio ~/.claude/skills/ && rm -rf /tmp/lcs
```

Or for one project only: copy `skills/line-character-studio` into `<project>/.claude/skills/`.

**claude.ai / Cowork** — download [`dist/line-character-studio.skill`](dist/line-character-studio.skill) and upload it in Settings → Capabilities → Skills.

Then just ask: *"make LINE stickers from my logo"*, *"create my character in different poses"*, *"ทำสติกเกอร์ไลน์"*, *"ทำธีมไลน์"*, *"ทำอีโมจิไลน์"*.

## You will need

- An **OpenAI API key** with credits (image generation is billed to your OpenAI account). On first use the skill asks for it; the safest way is to run the included helper in your own terminal so the key never enters the chat:
  ```bash
  python3 ~/.claude/skills/line-character-studio/scripts/set_api_key.py
  ```
  The key is stored only in the skill folder's `.env` (readable only by you) and checked with a free API call. `.env` is git-ignored — never commit it.
- Python 3.9+ with Pillow, numpy and scipy (`pip install pillow numpy scipy`).
- A LINE Creators Market account to submit the results.

## What it makes

| Product | What you get |
|---|---|
| **Character** | Your mascot in 20+ action poses (transparent PNGs) + an overview sheet — also handy for presentations |
| **Stickers** | 8/16/24/32/40 stickers (370×320, even sizes, 10 px margin), with or without captions, plus main + tab images |
| **Theme** | All 62 images: store thumbnails, 9 menu buttons × on/off for older iOS/Android **and iOS 26**, menu background, passcode, profile pictures, chat backgrounds |
| **Emoji** | 8–40 face emoji (180×180) + tab image |

Every package is checked against LINE's file names, sizes, transparency and 1 MB limits, and zipped flat the way the Creators Market uploader expects.

## Folder Structure

```
skills/line-character-studio/
  SKILL.md                     # the workflow: key → character → stickers / theme / emoji → deliver
  scripts/
    set_api_key.py             # ask for + verify + store the OpenAI key (never printed)
    gen_images.py              # parallel GPT Image generation / editing from a reference logo
    clean_png.py               # fix gpt-image transparency (alpha snap, hidden glow, trim)
    contact_sheet.py           # overview sheet of all poses
    make_stickers.py           # sticker layout: caption search, sign/ledge/banner modes, die-cut border
    finalize_line.py           # trim to LINE rules, validate, flat ZIP
    sticker_preview.py         # stickers on light/dark chat backgrounds
    make_theme.py              # all 62 theme images (brand colours via --primary/--secondary)
    finalize_theme.py          # validate theme + ZIP
    theme_preview.py           # phone mockup, menu bars (incl. iOS 26 light/dark), passcode, profiles
    make_chatbg.py             # custom chat-background scenes → iOS/Android sizes under 1 MB
    make_emoji.py              # emoji set + tab + ZIP + preview
  assets/                      # prompt templates and pose / theme / emoji prompt lists
  references/line-specs.md     # LINE sticker / theme / emoji specs with links to the official pages
dist/line-character-studio.skill   # packaged skill for claude.ai upload
```

## Good to know

- Captions are drawn in code, never by the image model (it misspells — especially Thai).
- LINE's specs change with app updates; `references/line-specs.md` records when they were verified and links to the official pages.
- Parodies of famous films or logos can be rejected by LINE review for paid items; the skill never draws copyrighted characters and keeps a safe backup.

## License

MIT
