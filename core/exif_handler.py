# Copyright (c) 2026 rkwithb (https://github.com/rkwithb)
# Licensed under CC BY-NC 4.0 (Non-Commercial Use Only)
# Disclaimer: Use at your own risk. The author is not responsible for any damages.

from datetime import datetime
from pathlib import Path

from core.logger import get_logger

logger = get_logger()

# Try to import piexif, make it optional
try:
    import piexif
    PIEXIF_AVAILABLE = True
except ImportError:
    PIEXIF_AVAILABLE = False


def is_exif_available() -> bool:
    """Return whether piexif module is installed and available."""
    return PIEXIF_AVAILABLE


def write_exif_time(file_path: Path, dt_obj: datetime) -> bool:
    """
    Write or correct the EXIF timestamp of a JPEG file.
    Only updates if the existing timestamp is missing or inconsistent.
    Skips non-JPEG files and when piexif is unavailable.
    Returns True if EXIF was written/updated, False otherwise.
    """
    # Skip non-JPEG files silently — expected behaviour, no log needed
    if not PIEXIF_AVAILABLE or file_path.suffix.lower() not in ['.jpg', '.jpeg']:
        return False

    target_time_str = dt_obj.strftime("%Y:%m:%d %H:%M:%S")

    try:
        exif_dict = piexif.load(str(file_path))

        # Read existing DateTimeOriginal field
        current_time = exif_dict.get("Exif", {}).get(piexif.ExifIFD.DateTimeOriginal)
        current_time_str = current_time.decode('utf-8') if isinstance(current_time, bytes) else current_time

        # Skip if timestamp is already correct
        if current_time_str == target_time_str:
            logger.debug(f"exif already correct, skipping: {file_path.name}")
            return False

        # Update all three EXIF time fields for consistency
        exif_dict["0th"][piexif.ImageIFD.DateTime]             = target_time_str
        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal]     = target_time_str
        exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized]    = target_time_str
        piexif.insert(piexif.dump(exif_dict), str(file_path))

        logger.debug(f"exif updated ({target_time_str}): {file_path.name}")
        return True

    except Exception as e:
        # Existing EXIF block is malformed or missing — fall back to writing a new block
        logger.warning(
            f"exif load failed, attempting fresh write: {file_path.name} — {type(e).__name__}: {e}"
        )
        try:
            new_exif = {
                "0th":  {piexif.ImageIFD.DateTime: target_time_str},
                "Exif": {
                    piexif.ExifIFD.DateTimeOriginal:  target_time_str,
                    piexif.ExifIFD.DateTimeDigitized: target_time_str,
                }
            }
            piexif.insert(piexif.dump(new_exif), str(file_path))
            logger.debug(f"exif fresh write OK ({target_time_str}): {file_path.name}")
            return True

        except Exception as e2:
            # Complete EXIF write failure — file may be locked or corrupted
            logger.error(
                f"exif write failed completely: {file_path.name} — {type(e2).__name__}: {e2}"
            )
            return False
