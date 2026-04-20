# Plurk Image Backup Tool CT — Developer Guide

---

## Prerequisites

### Python

Python **3.10 or higher** is required.

Download from [https://www.python.org](https://www.python.org).

### tkinter

tkinter is part of Python's standard library but must be installed separately on some Linux systems.

| Platform | How to install tkinter |
|---|---|
| Ubuntu / Debian | `sudo apt install python3-tk` |
| Fedora | `sudo dnf install python3-tkinter` |
| macOS | Install Python from [python.org](https://www.python.org) — tkinter is included |
| Windows | tkinter is bundled with the standard Python installer |

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/rkwithb/Plurk-Image-Backup-Tool-CT.git
cd Plurk-Image-Backup-Tool-CT
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv .venv

# Activate — Linux / macOS
source .venv/bin/activate

# Activate — Windows
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Dependencies include: `customtkinter`, `requests`, `piexif`, and their transitive deps.
`piexif` is optional at runtime — the tool runs without it, but the EXIF write feature will be disabled.

---

## Running from source

### GUI mode

```bash
python ui/app.py
```

### CLI mode

```bash
python main.py
```

The CLI expects your backup data at:
- `data/plurks/` — JS files for main posts
- `data/responses/` — JS files for replies

Output is written to `plurk_images_by_date/` in the current working directory.

The expected directory layout when running CLI mode:

```
Plurk-Image-Backup-Tool-CT/
├── main.py                        ← run from here
├── ... (other project files)
├── your-plurk-backup/             ← your backup folder (any name), place here
│   └── data/
│       ├── plurks/
│       └── responses/
└── plurk_images_by_date/          ← auto-generated on first run
    └── 2021-03-15/
        └── image.jpg
```

#### Language flag

The CLI defaults to the language saved in `config.json` (defaults to `zh_TW` on first run).
You can override it with the `--lang` flag, which also persists the choice for future runs:

```bash
python main.py --lang en
python main.py --lang zh_TW
```

---

## Project structure

```
Plurk-Image-Backup-Tool-CT/
├── main.py                  # CLI entry point
├── requirements.txt         # Python dependencies
├── config.json              # Persisted language setting
│
├── ui/
│   └── app.py               # GUI entry point (customtkinter)
│
├── core/
│   ├── processor.py         # Orchestrates prescan and full backup runs
│   ├── parser.py            # Parses Plurk JS backup files, extracts image URLs
│   ├── downloader.py        # Downloads images with rate limiting and backoff
│   ├── exif_handler.py      # Writes EXIF timestamps to JPEG files (piexif)
│   ├── i18n.py              # Lightweight i18n — loads locale JSON, t() helper
│   └── logger.py            # Singleton file logger, session headers, shutdown
│
├── locales/
│   ├── en.json              # English translations
│   └── zh_TW.json           # Traditional Chinese translations
│
└── readme/
    ├── README_user_en.md
    ├── README_user_zh-TW.md
    ├── README_dev_en.md
    └── README_dev_zh-TW.md
```

### Key design notes

`core/logger.py` uses line-buffered file I/O (`buffering=1`) so every log line is flushed to disk immediately — safe against crashes and force-kills.

`core/downloader.py` tracks consecutive failures per domain and applies automatic backoff on HTTP 429 responses, to avoid hammering servers.

`core/i18n.py` is a flat-key JSON system. All UI strings are accessed via `t("key")`. Language is persisted in `config.json` and reloaded on next launch. The GUI restarts the process on language change via `os.execv`.

---

## License

Licensed under [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) — Non-commercial use only.

> Disclaimer: Use at your own risk. The author is not responsible for any damages.
