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
from core.i18n import load_config, load_language, save_config, t, SUPPORTED_LANGUAGES

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


# --- Default path settings ---
DEFAULT_PLURKS_DIR = Path("data/plurks")
DEFAULT_RESPONSES_DIR = Path("data/responses")
DEFAULT_OUTPUT_ROOT = Path("plurk_images_by_date")


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


def _parse_lang_flag() -> str | None:
    """
    Parse --lang <code> from sys.argv.
    Returns the language code if provided and valid, otherwise None.

    Usage:
        python main.py --lang en
        python main.py --lang zh_TW
    """
    args = sys.argv[1:]
    if "--lang" not in args:
        return None

    idx = args.index("--lang")

    # --lang provided but no value follows it
    if idx + 1 >= len(args):
        print("Usage: python main.py --lang <code>")
        print(f"Supported languages: {', '.join(SUPPORTED_LANGUAGES.keys())}")
        sys.exit(1)

    lang = args[idx + 1]

    # Validate against supported languages
    if lang not in SUPPORTED_LANGUAGES:
        print(f"Unknown language '{lang}'. Supported: {', '.join(SUPPORTED_LANGUAGES.keys())}")
        sys.exit(1)

    return lang


def main():
    # Parse --lang flag before loading config — flag takes priority and persists
    lang_flag = _parse_lang_flag()

    if lang_flag:
        # Save the requested language to config.json so it persists for future runs
        save_config(lang_flag)
        lang = lang_flag
    else:
        # No flag — load from persisted config, defaulting to zh_TW on first run
        lang = load_config()

    load_language(lang)

    # Initialize file logger at CLI launch — before any user interaction
    setup_logger(mode="CLI")
    logger = get_logger()

    # Register excepthook so unhandled exceptions are captured in the log file.
    # In CLI mode there is no worker thread, so threading.excepthook is not needed.
    def _cli_excepthook(exc_type, exc_value, exc_tb):
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.critical(f"Unhandled exception in CLI:\n{tb_text}")
        shutdown_logger(reason="exception")
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _cli_excepthook

    print(t("cli_title"))
    print(t("cli_divider"))

    logger.info("CLI started")
    logger.info(f"Language : {lang}{' (--lang flag)' if lang_flag else ' (config)'}")

    # --- Folder settings ---
    plurks_dir = DEFAULT_PLURKS_DIR
    responses_dir = DEFAULT_RESPONSES_DIR
    output_root = DEFAULT_OUTPUT_ROOT

    logger.info(f"Input  plurks    : {plurks_dir}")
    logger.info(f"Input  responses : {responses_dir}")
    logger.info(f"Output root      : {output_root}")

    # --- EXIF option ---
    do_exif = False
    if is_exif_available():
        choice = safe_input(t("cli_exif_prompt"))
        do_exif = (choice == 'y')
    else:
        print(t("cli_no_piexif"))
        logger.warning("piexif not available — running in download-only mode")

    logger.info(f"EXIF   : {do_exif}")
    print()

    # Use try/finally to guarantee shutdown_logger() is always called,
    # even if run_full_backup() raises an unexpected exception mid-run.
    try:
        logger.info("--- Backup run started ---")
        stats = run_full_backup(
            plurks_dir=plurks_dir,
            responses_dir=responses_dir,
            output_root=output_root,
            do_exif=do_exif,
            on_log=print,
            on_progress=None,  # CLI mode does not use a progress bar
        )

        # --- Results summary ---
        print()
        print(t("cli_divider"))
        print(t("cli_result_title"))
        print(t("cli_result_downloaded", count=stats.downloaded))
        print(t("cli_result_skipped",    count=stats.skipped))
        print(t("cli_result_failed",     count=stats.failed))
        if do_exif:
            print(t("cli_result_exif",   count=stats.exif_updated))
        print(t("cli_divider"))

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
