# Copyright (c) 2026 rkwithb (https://github.com/rkwithb)
# Licensed under CC BY-NC 4.0 (Non-Commercial Use Only)
# Disclaimer: Use at your own risk. The author is not responsible for any damages.

import requests
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass

from core.exif_handler import write_exif_time
from core.logger import get_logger

logger = get_logger()

# Minimum file size to accept as a valid image (5KB)
MIN_IMAGE_SIZE = 5120


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
    Returns a DownloadResult dataclass.
    """
    # Extract filename from URL, strip query string
    file_name = url.split('/')[-1].split('?')[0]
    save_path = target_folder / file_name
    target_folder.mkdir(exist_ok=True, parents=True)

    # File already exists — skip download, optionally update EXIF
    if save_path.exists():
        logger.debug(f"skip (exists): {file_name}")
        exif_updated = write_exif_time(save_path, dt_obj) if do_exif else False
        return DownloadResult(skipped=True, exif_updated=exif_updated)

    # Log the attempt before making the request
    logger.debug(f"attempting download: {url}")

    # Attempt download
    try:
        res = requests.get(url, timeout=15)

        if res.status_code != 200:
            # Non-200 response — likely deleted or moved image
            logger.warning(
                f"download failed (HTTP {res.status_code}): {url}"
            )
            return DownloadResult(failed=True)

        if len(res.content) <= MIN_IMAGE_SIZE:
            # File too small — likely a placeholder or error page returned as 200
            logger.warning(
                f"download rejected (size {len(res.content)}B <= {MIN_IMAGE_SIZE}B): {url}"
            )
            return DownloadResult(failed=True)

        # Write file to disk
        with open(save_path, "wb") as f:
            f.write(res.content)

        logger.debug(f"downloaded OK ({len(res.content)}B): {file_name}")

        exif_updated = write_exif_time(save_path, dt_obj) if do_exif else False
        return DownloadResult(downloaded=True, exif_updated=exif_updated)

    except requests.exceptions.Timeout:
        logger.error(f"download timeout (15s): {url}")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"download connection error: {url} — {e}")
    except OSError as e:
        logger.error(f"file write error: {save_path} — {e}")
    except Exception as e:
        logger.error(f"download unexpected error: {url} — {type(e).__name__}: {e}")

    return DownloadResult(failed=True)
