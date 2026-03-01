# Copyright (c) 2026 rkwithb (https://github.com/rkwithb)
# Licensed under CC BY-NC 4.0 (Non-Commercial Use Only)
# Disclaimer: Use at your own risk. The author is not responsible for any damages.

import sys
import io
import os
import traceback
from pathlib import Path

from core.processor import run_full_backup
from core.exif_handler import is_exif_available
from core.logger import setup_logger, get_logger, shutdown_logger

# ==========================================
# Windows stdout robustness initialization
# Prevents encoding crashes in Windows terminal environments
# ==========================================
if sys.platform == "win32":
    if sys.stdout is not None and hasattr(sys.stdout, 'buffer'):
        try:
            # Force UTF-8 with line buffering to prevent encoding crashes
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
        except Exception:
            pass
    elif sys.stdout is None:
        # Prevent print crashes in --windowed mode or no-console environments
        sys.stdout = open(os.devnull, 'w')


# --- 預設路徑設定 ---
DEFAULT_PLURKS_DIR    = Path("data/plurks")
DEFAULT_RESPONSES_DIR = Path("data/responses")
DEFAULT_OUTPUT_ROOT   = Path("plurk_images_by_date")


def safe_input(prompt: str, default: str = "n") -> str:
    """
    Robust input function for CLI mode.
    Returns default value if not running in an interactive terminal,
    or if stdin is interrupted (e.g. GitHub Actions, piped input).
    """
    try:
        if not sys.stdin or not sys.stdin.isatty():
            return default
        return input(prompt).lower()
    except (EOFError, OSError):
        return default


def main():
    # Initialize file logger at CLI launch — before any user interaction
    log_path = setup_logger(mode="CLI")
    logger   = get_logger()

    # Register excepthook so unhandled exceptions are captured in the log file.
    # In CLI mode there is no worker thread, so threading.excepthook is not needed.
    def _cli_excepthook(exc_type, exc_value, exc_tb):
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.critical(f"Unhandled exception in CLI:\n{tb_text}")
        shutdown_logger(reason="exception")
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _cli_excepthook

    print("🚀 噗浪 JS 備份圖檔整理工具")
    print("=" * 40)

    logger.info("CLI started")

    # --- 資料夾設定 ---
    plurks_dir    = DEFAULT_PLURKS_DIR
    responses_dir = DEFAULT_RESPONSES_DIR
    output_root   = DEFAULT_OUTPUT_ROOT

    logger.info(f"Input  plurks    : {plurks_dir}")
    logger.info(f"Input  responses : {responses_dir}")
    logger.info(f"Output root      : {output_root}")

    # --- EXIF 選項 ---
    do_exif = False
    if is_exif_available():
        choice  = safe_input("👉 是否要檢查並補寫/覆蓋圖檔的 EXIF 圖片時間？(y/N)：")
        do_exif = (choice == 'y')
    else:
        print("💡 提示：未安裝 piexif 模組，將以純下載模式執行。")
        logger.warning("piexif not available — running in download-only mode")

    logger.info(f"EXIF   : {do_exif}")
    print()

    # Use try/finally to guarantee shutdown_logger() is always called,
    # even if run_full_backup() raises an unexpected exception mid-run.
    try:
        # --- 執行備份，log callback 直接 print ---
        logger.info("--- Backup run started ---")
        stats = run_full_backup(
            plurks_dir=plurks_dir,
            responses_dir=responses_dir,
            output_root=output_root,
            do_exif=do_exif,
            on_log=print,
            on_progress=None,  # CLI mode does not use progress bar
        )

        # --- 結果摘要 ---
        print()
        print("=" * 40)
        print("✨ 備份整理結果：")
        print(f"  📥 新下載圖片：{stats.downloaded} 張")
        print(f"  ⏭️  略過已存在/過小圖片：{stats.skipped} 張")
        print(f"  ❌ 下載失敗：{stats.failed} 張")
        if do_exif:
            print(f"  🕒 覆寫/校正 EXIF 標頭：{stats.exif_updated} 張")
        print("=" * 40)

        logger.info("--- Backup run completed ---")
        logger.info(f"Downloaded : {stats.downloaded}")
        logger.info(f"Skipped    : {stats.skipped}")
        logger.info(f"Failed     : {stats.failed}")
        logger.info(f"EXIF       : {stats.exif_updated}")

    finally:
        # Always flush and close the log file cleanly on exit
        shutdown_logger(reason="normal")


if __name__ == "__main__":
    main()
