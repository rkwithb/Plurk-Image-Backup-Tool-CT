# Copyright (c) 2026 rkwithb (https://github.com/rkwithb)
# Licensed under CC BY-NC 4.0 (Non-Commercial Use Only)
# Disclaimer: Use at your own risk. The author is not responsible for any damages.

"""
core/logger.py

Centralized singleton logger for plurk-image-dl-ct.
- Call setup_logger() once at app launch (GUI or CLI).
- All other modules use get_logger() to obtain the shared logger instance.
- Log files are written to <program_folder>/log/session_YYYYMMDD_HHMMSS.log
- Works in both script mode and PyInstaller frozen .exe mode.
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
    now      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os_info  = f"{platform.system()} {platform.release()}"
    py_ver   = platform.python_version()

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

    # File handler — UTF-8 to safely handle CJK characters in paths
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    # Log format: timestamp [LEVEL ] [module] message
    formatter = logging.Formatter(
        fmt     = "%(asctime)s [%(levelname)-5s] [%(module)s] %(message)s",
        datefmt = "%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Store log path on the handler for later retrieval
    file_handler._log_path = str(log_path)

    # Write session header as first log entry
    header = _build_session_header(log_path, mode)
    logger.info("\n" + header)

    _initialized = True
    return log_path


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
    Retrieve the log file path from an already-initialized logger's file handler.
    Returns a fallback Path if no file handler is found.
    """
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            return Path(handler.baseFilename)
    return Path("log/unknown.log")
