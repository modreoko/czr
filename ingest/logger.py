"""
Centralized logging configuration for the zmluvy project.
Supports logging to both console and file (incremental).
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

# Log directory
LOG_DIR = Path(__file__).parent.parent / "log"

# Ensure log directory exists
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Log file path (incremental)
LOG_FILE = LOG_DIR / "debug.log"


def setup_logging(enable_logging: bool = False) -> logging.Logger:
    """
    Configure logging for the project.

    Args:
        enable_logging: If True, logs to both console and file.
                       If False, only logs to console.

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("zmluvy")
    logger.setLevel(logging.DEBUG)

    # Remove any existing handlers
    logger.handlers.clear()

    # Console handler (always enabled)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler (only if enabled) - INCREMENTAL (append mode)
    if enable_logging:
        file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

        # Log initialization message
        logger.info("=" * 80)
        logger.info(f"[START] LOGGING STARTED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"[FILE] Log file: {LOG_FILE}")
        logger.info("=" * 80)

    return logger


def get_logger() -> logging.Logger:
    """Get the configured logger instance."""
    return logging.getLogger("zmluvy")
