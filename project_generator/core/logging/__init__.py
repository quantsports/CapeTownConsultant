"""
Logging facade.
Re-exports `logger` so existing imports continue to work:
    from src.core.logging import logger
"""
from .setup import logger, configure_logging

__all__ = ["logger", "configure_logging"]
