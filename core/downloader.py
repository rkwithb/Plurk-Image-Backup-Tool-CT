# Copyright (c) 2026 rkwithb (https://github.com/rkwithb)
# Licensed under CC BY-NC 4.0 (Non-Commercial Use Only)
# Disclaimer: Use at your own risk. The author is not responsible for any damages.

import requests
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass

from core.exif_handler import write_exif_time

# Minimum file size to accept as a valid image (5KB)
MIN_IMAGE_SIZE = 5120


@dataclass
class DownloadResult:
    """
    Structured result for a single image download attempt.
    downloaded: True if the file was newly downloaded.
    skipped:    True if the file already existed.
    exif_updated: True if EXIF timestamp was written or corrected.
    failed:     True if download was attempted but failed.
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
        exif_updated = write_exif_time(save_path, dt_obj) if do_exif else False
        return DownloadResult(skipped=True, exif_updated=exif_updated)

    # Attempt download
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200 and len(res.content) > MIN_IMAGE_SIZE:
            with open(save_path, "wb") as f:
                f.write(res.content)
            exif_updated = write_exif_time(save_path, dt_obj) if do_exif else False
            return DownloadResult(downloaded=True, exif_updated=exif_updated)
    except Exception:
        pass

    return DownloadResult(failed=True)
