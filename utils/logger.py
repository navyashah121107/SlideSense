"""Logging setup for the project.

Role: configure a rotating file handler (``logs/game.log``) plus a console
handler on the ``puzzle`` logger namespace. Nothing happens on import; call
``setup_logging()`` once from ``main.py``. Modules obtain loggers through
``get_logger(__name__)``.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from utils.config import (
    LOG_BACKUP_COUNT,
    LOG_DATE_FORMAT,
    LOG_FILE,
    LOG_FORMAT,
    LOG_MAX_BYTES,
    LOGGER_ROOT_NAME,
)

_configured = False


def setup_logging(
    level: int = logging.INFO,
    log_file: Path = LOG_FILE,
    console: bool = True,
) -> logging.Logger:
    """Configure project-wide logging (idempotent).

    Args:
        level: Minimum severity to record.
        log_file: Destination of the rotating log file.
        console: Also stream records to stderr when True.

    Returns:
        The configured ``puzzle`` root logger.
    """
    global _configured
    root = logging.getLogger(LOGGER_ROOT_NAME)
    if _configured:
        return root

    root.setLevel(level)
    root.propagate = False
    formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)

    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    if console:
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setFormatter(formatter)
        root.addHandler(stream_handler)

    _configured = True
    return root


def get_logger(name: str) -> logging.Logger:
    """Return a child logger inside the project namespace.

    Args:
        name: Usually ``__name__`` of the calling module.

    Returns:
        A ``logging.Logger`` named ``puzzle.<name>``.
    """
    return logging.getLogger(f"{LOGGER_ROOT_NAME}.{name}")


if __name__ == "__main__":
    setup_logging()
    get_logger(__name__).info("Logger demo: written to %s", LOG_FILE)
