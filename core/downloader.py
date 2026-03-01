# Copyright (c) 2026 rkwithb (https://github.com/rkwithb)
# Licensed under CC BY-NC 4.0 (Non-Commercial Use Only)
# Disclaimer: Use at your own risk. The author is not responsible for any damages.

import time
import requests
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from urllib.parse import urlparse

from core.exif_handler import write_exif_time
from core.logger import get_logger

logger = get_logger()

# ==========================================
# Download behaviour constants
# ==========================================

# Minimum file size to accept as a valid image (5KB)
MIN_IMAGE_SIZE = 5120

# Fixed polite delay between every successful download request (seconds).
# Applied after a successful download only — not on skip, backoff, or failure.
DELAY_BETWEEN_REQUESTS = 0.1

# Backoff duration when server responds with HTTP 429 Too Many Requests (seconds).
# Replaces the normal delay — not added on top of it.
BACKOFF_ON_429 = 8.0

# Backoff duration when the same domain fails consecutively (seconds).
# Replaces the normal delay — not added on top of it.
BACKOFF_ON_REPEAT_FAIL = 6.0

# Number of consecutive failures from the same domain before backoff triggers.
REPEAT_FAIL_THRESHOLD = 3

# ==========================================
# Module-level domain failure tracker
# ==========================================
# Tracks consecutive failure count per domain across the entire session.
# Keyed by domain string (e.g. "images.plurk.com").
# Resets to 0 on first successful download from that domain.
# Module-level so state persists across all download_image() calls in one run.
_domain_fail_count: dict[str, int] = {}


@dataclass
class DownloadResult:
    """
    Structured result for a single image download attempt.
    downloaded:   True if the file was newly downloaded.
    skipped:      True if the file already existed.
    exif_updated: True if EXIF timestamp was written or corrected.
    failed:       True if download was attempted but failed.
    """
    downloaded: bool = False
    skipped: bool = False
    exif_updated: bool = False
    failed: bool = False


def _extract_domain(url: str) -> str:
    """Extract the netloc domain from a URL for use as a failure tracker key."""
    try:
        return urlparse(url).netloc
    except Exception:
        return "unknown"


def _record_failure(domain: str) -> None:
    """
    Increment the consecutive failure count for a domain.
    If the count reaches REPEAT_FAIL_THRESHOLD, sleep BACKOFF_ON_REPEAT_FAIL.
    Backoff replaces the normal per-request delay — not added on top.
    """
    _domain_fail_count[domain] = _domain_fail_count.get(domain, 0) + 1
    count = _domain_fail_count[domain]

    if count >= REPEAT_FAIL_THRESHOLD:
        logger.warning(
            f"domain '{domain}' failed {count} times consecutively — "
            f"backing off {BACKOFF_ON_REPEAT_FAIL}s"
        )
        time.sleep(BACKOFF_ON_REPEAT_FAIL)


def _record_success(domain: str) -> None:
    """
    Reset the failure count for a domain after a successful download,
    then apply the standard polite delay between requests.
    """
    if _domain_fail_count.get(domain, 0) > 0:
        logger.debug(f"domain '{domain}' recovered — resetting fail count")
    _domain_fail_count[domain] = 0
    time.sleep(DELAY_BETWEEN_REQUESTS)


def download_image(
    url: str,
    target_folder: Path,
    dt_obj: datetime,
    do_exif: bool
) -> DownloadResult:
    """
    Download a single image to target_folder.
    Skips if file already exists (optionally updates EXIF).
    Rejects files smaller than MIN_IMAGE_SIZE to filter out broken images.

    Delay behaviour:
        - Every successful download sleeps DELAY_BETWEEN_REQUESTS afterward.
        - HTTP 429 response sleeps BACKOFF_ON_429 (replaces normal delay).
        - REPEAT_FAIL_THRESHOLD consecutive failures from same domain
          sleeps BACKOFF_ON_REPEAT_FAIL (replaces normal delay).
        - Skipped files (already exist) have no delay — no request was made.

    Returns a DownloadResult dataclass.
    """
    # Extract filename from URL, strip query string
    file_name = url.split('/')[-1].split('?')[0]
    save_path = target_folder / file_name
    target_folder.mkdir(exist_ok=True, parents=True)

    # File already exists — skip download, optionally update EXIF
    # No delay applied: no network request was made
    if save_path.exists():
        logger.debug(f"skip (exists): {file_name}")
        exif_updated = write_exif_time(save_path, dt_obj) if do_exif else False
        return DownloadResult(skipped=True, exif_updated=exif_updated)

    domain = _extract_domain(url)
    logger.debug(f"attempting download: {url}")

    try:
        res = requests.get(url, timeout=15)

        # 429 Too Many Requests — server is explicitly rate limiting us
        # Apply dedicated backoff, do not add normal delay on top
        if res.status_code == 429:
            logger.warning(
                f"HTTP 429 Too Many Requests — backing off {BACKOFF_ON_429}s: {url}"
            )
            _domain_fail_count[domain] = _domain_fail_count.get(domain, 0) + 1
            time.sleep(BACKOFF_ON_429)
            return DownloadResult(failed=True)

        # Other non-200 response — likely deleted or moved image
        if res.status_code != 200:
            logger.warning(f"download failed (HTTP {res.status_code}): {url}")
            _record_failure(domain)
            return DownloadResult(failed=True)

        # File too small — likely a residual thumbnail or placeholder returned as 200.
        # This is our own content filter decision, not a server rejection or error.
        # Returned as skipped=True (not failed) because:
        #   - The server responded correctly
        #   - No backoff should be triggered
        #   - It folds into the '略過已存在/過小圖片' stat alongside existing files,
        #     which is accurate — both are intentional non-downloads, not failures
        # Do NOT call _record_failure() here.
        if len(res.content) <= MIN_IMAGE_SIZE:
            logger.debug(
                f"download skipped (size {len(res.content)}B <= {MIN_IMAGE_SIZE}B): {url}"
            )
            return DownloadResult(skipped=True)

        # Write file to disk
        with open(save_path, "wb") as f:
            f.write(res.content)

        logger.debug(f"downloaded OK ({len(res.content)}B): {file_name}")

        exif_updated = write_exif_time(save_path, dt_obj) if do_exif else False

        # Success — reset domain fail count and apply polite delay
        _record_success(domain)
        return DownloadResult(downloaded=True, exif_updated=exif_updated)

    except requests.exceptions.Timeout:
        logger.error(f"download timeout (15s): {url}")
        _record_failure(domain)
    except requests.exceptions.ConnectionError as e:
        logger.error(f"download connection error: {url} — {e}")
        _record_failure(domain)
    except OSError as e:
        logger.error(f"file write error: {save_path} — {e}")
        # OSError is a local disk issue, not a domain issue — do not penalise domain
    except Exception as e:
        logger.error(f"download unexpected error: {url} — {type(e).__name__}: {e}")
        _record_failure(domain)

    return DownloadResult(failed=True)