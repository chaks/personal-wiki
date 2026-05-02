from __future__ import annotations
# src/logging_config.py
"""Centralized logging configuration for Personal Wiki Chat."""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(
    log_dir: Path | None = None,
    level: int = logging.INFO,
    file_level: int = logging.DEBUG,
) -> None:
    """Configure logging with console and file handlers.

    Args:
        log_dir: Directory for log files. Defaults to project_root/logs.
        level: Logging level for console handler (default: INFO).
        file_level: Logging level for file handler (default: DEBUG).
    """
    root = Path(__file__).parent.parent
    log_dir = log_dir or (root / "logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "personal-wiki.log"

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(min(level, file_level))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler - human readable
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler - rotating, detailed
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    file_handler.setLevel(file_level)
    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(funcName)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    logging.getLogger("src").setLevel(min(level, file_level))
