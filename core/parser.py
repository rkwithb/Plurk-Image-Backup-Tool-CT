# Copyright (c) 2026 rkwithb (https://github.com/rkwithb)
# Licensed under CC BY-NC 4.0 (Non-Commercial Use Only)
# Disclaimer: Use at your own risk. The author is not responsible for any damages.

import re
import json
from pathlib import Path

from core.logger import get_logger

logger = get_logger()

# Regex: exclude official Plurk stickers, match general image files
PLURK_EMOJI_PATTERN = re.compile(r'https://images\.plurk\.com/mx_')
GENERAL_IMAGE_PATTERN = re.compile(r'https?://[^\s"\'\\]+\.(?:jpg|png|gif|jpeg)', re.IGNORECASE)


def parse_js_content(file_path: Path) -> list:
    """
    Parse a Plurk JS backup file and return a list of post items.
    Handles the 'var BackupData = [...];' format.
    Returns empty list on any failure.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read().strip()

            # Find the '=' sign to locate the JSON array
            eq_index = raw_text.find('=')
            if eq_index == -1:
                logger.warning(f"parse_js_content: no '=' found in file — {file_path}")
                return []

            json_part = raw_text[eq_index + 1:].strip()

            # Remove trailing semicolon if present
            if json_part.endswith(';'):
                json_part = json_part[:-1].strip()

            result = json.loads(json_part, strict=False)

            # Only return if result is a list of dicts (plurks/responses format)
            if not isinstance(result, list):
                logger.warning(f"parse_js_content: parsed result is not a list ({type(result).__name__}) — {file_path}")
                return []

            logger.debug(f"parse_js_content: OK — {file_path.name} ({len(result)} items)")
            return result

    except json.JSONDecodeError as e:
        logger.error(f"parse_js_content: JSON decode error in {file_path.name} — {e}")
        return []
    except OSError as e:
        logger.error(f"parse_js_content: cannot read file {file_path} — {e}")
        return []
    except Exception as e:
        logger.error(f"parse_js_content: unexpected error in {file_path.name} — {type(e).__name__}: {e}")
        return []


def get_all_valid_images(text_content: str) -> set:
    """
    Extract valid image URLs from post content.
    Excludes Plurk official stickers (mx_ prefix) and system images (emos/static domains).
    Returns a set of URL strings.
    """
    if not text_content:
        return set()

    # Normalize escaped slashes from JSON encoding
    clean_text = text_content.replace('\\/', '/')
    all_urls = GENERAL_IMAGE_PATTERN.findall(clean_text)

    valid_urls = set()
    for url in all_urls:
        low_url = url.lower()

        # Skip Plurk system image domains (UI chrome, not user content)
        if "emos.plurk.com" in low_url or "static.plurk.com" in low_url:
            continue

        # Skip Plurk user avatars — these are account profile pictures embedded
        # as preview thumbnails in linked plurk HTML, not actual post content images.
        # They consistently fail MIN_IMAGE_SIZE and are never worth downloading.
        if "avatars.plurk.com" in low_url:
            continue

        # Skip Plurk emoticons served from s.plurk.com/emoticons — tiny GIFs
        # (basic, silver, gold, platinum tiers). Same rationale as emos.plurk.com —
        # Plurk's emoticon CDN, not user-uploaded content.
        if "s.plurk.com/emoticons" in low_url:
            continue

        # Skip Plurk auto-generated medium thumbnails (_mt suffix).
        # Plurk generates _mt.jpg as a smaller version of every uploaded image.
        # The full-size original (without _mt) is the version worth downloading
        # and will be captured separately from the same post content.
        if "imgs.plurk.com" in low_url and "_mt.jpg" in low_url:
            continue

        # Skip YouTube default thumbnails (120x90px, ~3-5KB) — always too small.
        # Only filter the 'default.jpg' variant to preserve larger thumbnails
        # (mqdefault, hqdefault, maxresdefault) in case they are ever linked directly.
        if "i.ytimg.com" in low_url and "default.jpg" in low_url:
            continue

        # Skip official Plurk stickers (mx_ prefix)
        if "images.plurk.com" in low_url and PLURK_EMOJI_PATTERN.search(url):
            continue

        valid_urls.add(url)

    return valid_urls
