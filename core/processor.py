# Copyright (c) 2026 rkwithb (https://github.com/rkwithb)
# Licensed under CC BY-NC 4.0 (Non-Commercial Use Only)
# Disclaimer: Use at your own risk. The author is not responsible for any damages.

from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable, Optional

from core.parser import parse_js_content, get_all_valid_images
from core.downloader import download_image, DownloadResult


@dataclass
class ProcessStats:
    """
    Aggregated statistics for a full processing run.
    downloaded:   total newly downloaded images.
    skipped:      total images that already existed.
    exif_updated: total images with EXIF timestamp written or corrected.
    failed:       total images that failed to download.
    """
    downloaded: int = 0
    skipped: int = 0
    exif_updated: int = 0
    failed: int = 0

    def merge(self, other: "ProcessStats") -> "ProcessStats":
        """Merge another ProcessStats into this one and return self."""
        self.downloaded += other.downloaded
        self.skipped += other.skipped
        self.exif_updated += other.exif_updated
        self.failed += other.failed
        return self


def process_folder(
    source_dir: Path,
    output_root: Path,
    label: str,
    do_exif: bool,
    on_log: Optional[Callable[[str], None]] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> ProcessStats:
    """
    Scan all JS backup files in source_dir and download images to output_root.
    Organizes downloaded images into subfolders by date (YYYY-MM-DD).

    Parameters:
        source_dir:   Path to folder containing Plurk JS backup files.
        output_root:  Root path where dated subfolders will be created.
        label:        Display label for logging (e.g. '主噗' / '回應').
        do_exif:      Whether to write EXIF timestamps to JPEG files.
        on_log:       Optional callback(message: str) for UI log output.
        on_progress:  Optional callback(current: int, total: int) for UI progress bar.

    Returns a ProcessStats dataclass.
    """
    stats = ProcessStats()

    def log(msg: str):
        # Route log messages to callback if provided, otherwise no-op (no print in core)
        if on_log:
            on_log(msg)

    if not source_dir.exists():
        log(f"⚠️ 找不到「{label}」資料夾，略過處理。")
        return stats

    # Collect all JS files first to support progress reporting
    js_files = list(source_dir.glob("*.js"))
    total_files = len(js_files)

    for file_index, js_file in enumerate(js_files):
        items = parse_js_content(js_file)
        if not items:
            continue

        log(f"📂 [{label}] 正在處理：{js_file.name}")

        for item in items:
            posted_date = item.get("posted", "")
            try:
                dt = datetime.strptime(posted_date, "%a, %d %b %Y %H:%M:%S GMT")
                # Organize into dated subfolders (YYYY-MM-DD)
                date_folder = output_root / dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

            # Combine content and content_raw for image URL extraction
            content = (item.get("content", "") or "") + " " + (item.get("content_raw", "") or "")
            urls = get_all_valid_images(content)

            for url in urls:
                result: DownloadResult = download_image(url, date_folder, dt, do_exif)

                if result.downloaded:
                    stats.downloaded += 1
                    log(f"  📥 下載完成：{url.split('/')[-1].split('?')[0]}")
                elif result.skipped:
                    stats.skipped += 1
                elif result.failed:
                    stats.failed += 1
                    log(f"  ❌ 下載失敗：{url}")

                if result.exif_updated:
                    stats.exif_updated += 1
                    log(f"  🕒 已更新 EXIF 圖檔時間：{url.split('/')[-1].split('?')[0]}")

        # Report progress after each JS file is processed
        if on_progress:
            on_progress(file_index + 1, total_files)

    return stats


def run_full_backup(
    plurks_dir: Path,
    responses_dir: Path,
    output_root: Path,
    do_exif: bool,
    on_log: Optional[Callable[[str], None]] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> ProcessStats:
    """
    Run full backup for both plurks and responses folders.
    Returns merged ProcessStats from both runs.
    """
    output_root.mkdir(exist_ok=True, parents=True)

    plurks_stats = process_folder(
        plurks_dir, output_root, "主噗", do_exif, on_log, on_progress
    )
    responses_stats = process_folder(
        responses_dir, output_root, "回應", do_exif, on_log, on_progress
    )

    return plurks_stats.merge(responses_stats)
