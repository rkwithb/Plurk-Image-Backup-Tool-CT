# Copyright (c) 2026 rkwithb (https://github.com/rkwithb)
# Licensed under CC BY-NC 4.0 (Non-Commercial Use Only)
# Disclaimer: Use at your own risk. The author is not responsible for any damages.

"""
core/logger.py

Centralized singleton logger for plurk-image-dl-ct.
- Call setup_logger() once at app launch (GUI or CLI).
- All other modules use get_logger() to obtain the shared logger instance.
- Call shutdown_logger() before exiting to flush and close the file cleanly.
- Log files are written to <program_folder>/log/session_YYYYMMDD_HHMMSS.log
- Works in both script mode and PyInstaller frozen .exe mode.

Buffering strategy:
  The file is opened in line-buffered mode (buffering=1).
  This means every log line is flushed to disk immediately after being written,
  rather than accumulating in an 8KB memory buffer first.
  Trade-off: slightly more disk write operations, but each line is guaranteed
  on disk before the next one is written — critical for crash/kill scenarios
  where a full-buffer flush would never happen.
  Performance impact is negligible since the bottleneck is network I/O, not disk.
"""

import logging
import platform
import sys
from datetime import datetime
from pathlib import Path

# Shared logger name used across all modules
_LOGGER_NAME = "plurk_dl"

# Tracks whether setup_logger() has already been called
_initialized = False


def _resolve_program_folder() -> Path:
    """
    Resolve the folder containing the running program.
    Handles both normal script execution and PyInstaller frozen .exe.
    """
    if getattr(sys, "frozen", False):
        # PyInstaller frozen executable — use the .exe directory
        return Path(sys.executable).resolve().parent
    else:
        # Normal script mode — use the project root (two levels up from this file)
        return Path(__file__).resolve().parent.parent


def _build_session_header(log_path: Path, mode: str) -> str:
    """
    Build a structured session header block written at the top of each log file.
    Captures environment snapshot for easy debugging.
    """
    now     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os_info = f"{platform.system()} {platform.release()}"
    py_ver  = platform.python_version()

    lines = [
        "=" * 56,
        "  Plurk Image DL — Session Start",
        f"  Time    : {now}",
        f"  OS      : {os_info}",
        f"  Python  : {py_ver}",
        f"  Mode    : {mode}",
        f"  Log     : {log_path}",
        "=" * 56,
    ]
    return "\n".join(lines)


def setup_logger(mode: str = "GUI") -> Path:
    """
    Initialize the singleton file logger. Should be called exactly once at app launch.

    Args:
        mode: "GUI" or "CLI" — recorded in the session header for context.

    Returns:
        Path to the log file created for this session.

    Behaviour:
        - Creates <program_folder>/log/ if it does not exist.
        - Names the file session_YYYYMMDD_HHMMSS.log.
        - Opens the file in line-buffered mode (buffering=1) so every line
          is written to disk immediately — safe against crashes and force-kills.
        - Writes a session header block as the first entry.
        - Subsequent calls are no-ops (returns the existing log path).
    """
    global _initialized

    logger = logging.getLogger(_LOGGER_NAME)

    # Guard: do not re-initialize if already set up
    if _initialized:
        return _get_existing_log_path(logger)

    logger.setLevel(logging.DEBUG)

    # Build log folder path
    program_folder = _resolve_program_folder()
    log_folder     = program_folder / "log"
    log_folder.mkdir(parents=True, exist_ok=True)

    # Timestamped session filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path  = log_folder / f"session_{timestamp}.log"

    # Open file in line-buffered mode (buffering=1):
    # Each log line is flushed to disk immediately after writing.
    # Default FileHandler would buffer ~8KB in memory before flushing —
    # meaning the last N lines before a crash or force-kill could be lost.
    log_file     = open(log_path, "a", encoding="utf-8", buffering=1)
    file_handler = logging.StreamHandler(log_file)
    file_handler.setLevel(logging.DEBUG)

    # Store the file object reference for clean shutdown later
    file_handler._log_file = log_file
    file_handler._log_path = str(log_path)

    # Log format: timestamp [LEVEL ] [module] message
    formatter = logging.Formatter(
        fmt     = "%(asctime)s [%(levelname)-5s] [%(module)s] %(message)s",
        datefmt = "%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Write session header as first log entry
    header = _build_session_header(log_path, mode)
    logger.info("\n" + header)

    _initialized = True
    return log_path


def shutdown_logger(reason: str = "normal") -> None:
    """
    Flush and close the log file cleanly before the app exits.
    Should be called from on_closing() or any exit path.

    Args:
        reason: short label recorded as the final log line.
                Use "normal" for clean exit, "user_closed" for window close,
                "interrupted" for mid-run close, "exception" for crash exit.

    Note: After shutdown_logger() is called, further log calls will be silent
    since all handlers are removed. This is intentional — it is the last thing
    called before the process exits.
    """
    logger = logging.getLogger(_LOGGER_NAME)
    logger.info(f"--- Session ended ({reason}) ---")

    # Flush and close all handlers, then remove them from the logger
    for handler in logger.handlers[:]:
        try:
            handler.flush()
            if hasattr(handler, "_log_file"):
                handler._log_file.close()
            handler.close()
        except Exception:
            pass
        logger.removeHandler(handler)


def get_logger() -> logging.Logger:
    """
    Return the shared logger instance.
    All modules should call this instead of logging.getLogger() directly,
    so the logger name stays consistent across the codebase.

    Note: setup_logger() must be called before this is useful.
    If called before setup, returns the logger with no handlers (silent).
    """
    return logging.getLogger(_LOGGER_NAME)


def _get_existing_log_path(logger: logging.Logger) -> Path:
    """
    Retrieve the log file path from an already-initialized logger's StreamHandler.
    Returns a fallback Path if no handler with a stored path is found.
    """
    for handler in logger.handlers:
        if hasattr(handler, "_log_path"):
            return Path(handler._log_path)
    return Path("log/unknown.log")
