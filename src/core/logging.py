"""
Logging configuration using Loguru
Structured logging with console and file outputs
"""

import sys
import json
from pathlib import Path
from loguru import logger as _loguru_logger
from src.config.settings import Config


class KvLogger:
    """Adapter to support logger.info('event', key=value) style calls"""

    def __init__(self, base):
        self._base = base

    def _emit(self, level: str, event: str, **kwargs):
        """Emit log with structured key-value pairs"""
        if kwargs:
            parts = []
            for k, v in kwargs.items():
                try:
                    val = json.dumps(v, default=str)
                except Exception:
                    val = str(v)
                parts.append(f"{k}={val}")
            msg = f"{event} | " + " ".join(parts)
        else:
            msg = event
        self._base.log(level.upper(), msg)

    def debug(self, event: str, **kwargs):
        self._emit("DEBUG", event, **kwargs)

    def info(self, event: str, **kwargs):
        self._emit("INFO", event, **kwargs)

    def warning(self, event: str, **kwargs):
        self._emit("WARNING", event, **kwargs)

    def error(self, event: str, **kwargs):
        self._emit("ERROR", event, **kwargs)

    def bind(self, **kwargs):
        return KvLogger(self._base.bind(**kwargs))


def setup_logging():
    """Configure logging with console and file outputs"""
    # Reset default sinks
    _loguru_logger.remove()

    # Console sink (colorized)
    _loguru_logger.add(
        sys.stdout,
        level=Config.LOG_LEVEL,
        enqueue=True,
        backtrace=False,
        diagnose=False,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level:<8}</level> | {message}"
    )

    # File sink (rotation + retention)
    _loguru_logger.add(
        str(Config.LOG_DIR / "app.log"),
        level=Config.LOG_LEVEL,
        rotation="10 MB",
        retention="14 days",
        enqueue=True,
        backtrace=False,
        diagnose=False,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {message}"
    )

    return KvLogger(_loguru_logger)


# Create global logger instance
logger = setup_logging()