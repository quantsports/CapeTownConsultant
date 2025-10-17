"""
Logging configuration using Loguru
Structured logging with console and file outputs
"""

import sys
import json
from pathlib import Path
from typing import Any, Dict, Optional
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
                except Exception as e:
                    # Fallback for objects that can't be serialized
                    try:
                        val = json.dumps(str(v))
                    except Exception:
                        val = f'"<unserializable: {type(v).__name__}>"'
                    # Log serialization issues at debug level
                    if level.upper() not in ("DEBUG",):
                        self._base.opt(depth=1).debug(
                            f"Serialization warning for key '{k}': {e.__class__.__name__}"
                        )
                parts.append(f"{k}={val}")
            msg = f"{event} | " + " ".join(parts)
        else:
            msg = event
        self._base.log(level.upper(), msg)

    def debug(self, event: str, **kwargs):
        """Log debug message with optional key-value pairs"""
        self._emit("DEBUG", event, **kwargs)

    def info(self, event: str, **kwargs):
        """Log info message with optional key-value pairs"""
        self._emit("INFO", event, **kwargs)

    def warning(self, event: str, **kwargs):
        """Log warning message with optional key-value pairs"""
        self._emit("WARNING", event, **kwargs)

    def error(self, event: str, **kwargs):
        """Log error message with optional key-value pairs"""
        self._emit("ERROR", event, **kwargs)

    def critical(self, event: str, **kwargs):
        """Log critical message with optional key-value pairs"""
        self._emit("CRITICAL", event, **kwargs)

    def exception(self, event: str, **kwargs):
        """Log exception with traceback and optional key-value pairs"""
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
        self._base.opt(exception=True).error(msg)

    def success(self, event: str, **kwargs):
        """Log success message with optional key-value pairs"""
        self._emit("SUCCESS", event, **kwargs)

    def bind(self, **kwargs):
        """Bind context variables that will be included in all subsequent logs"""
        return KvLogger(self._base.bind(**kwargs))

    def opt(self, **kwargs):
        """Configure logger options (depth, exception, etc.)"""
        return KvLogger(self._base.opt(**kwargs))


def setup_logging():
    """Configure logging with console and file outputs
    
    Features:
    - Console output with colors
    - File rotation at 10 MB with compression
    - 14-day retention policy
    - Async enqueueing for better performance
    - Separate error log file for ERROR and above
    """
    # Reset default sinks
    _loguru_logger.remove()

    # Console sink (colorized, human-readable)
    try:
        _loguru_logger.add(
            sys.stdout,
            level=Config.LOG_LEVEL,
            enqueue=True,
            backtrace=False,
            diagnose=False,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level:<8}</level> | {message}",
            catch=True  # Catch errors in logging itself
        )
    except Exception as e:
        print(f"Warning: Could not setup console logging: {e}", file=sys.stderr)

    # Main file sink (rotation + retention + compression)
    try:
        _loguru_logger.add(
            str(Config.LOG_DIR / "app.log"),
            level=Config.LOG_LEVEL,
            rotation="10 MB",
            retention="14 days",
            compression="gz",  # Compress rotated files
            enqueue=True,
            backtrace=False,
            diagnose=False,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {message}",
            catch=True,
            encoding="utf-8"  # Explicit encoding for better compatibility
        )
    except Exception as e:
        print(f"Warning: Could not setup file logging: {e}", file=sys.stderr)

    # Error file sink (separate file for errors, with more context)
    try:
        _loguru_logger.add(
            str(Config.LOG_DIR / "errors.log"),
            level="ERROR",
            rotation="5 MB",
            retention="30 days",  # Keep errors longer
            compression="gz",
            enqueue=True,
            backtrace=True,  # Include backtrace for errors
            diagnose=False,  # Don't include variable values (security)
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} | {message}",
            catch=True,
            encoding="utf-8"
        )
    except Exception as e:
        print(f"Warning: Could not setup error logging: {e}", file=sys.stderr)

    return KvLogger(_loguru_logger)


# Create global logger instance
logger = setup_logging()