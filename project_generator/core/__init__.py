"""
Core package exports (backward compatible).
"""
from src.core.logging import logger, configure_logging
from src.core.models import ToolType, ToolResult, Message, CitationManager
from src.core.cache import LRUCache, PersistentEmbeddingCache
from src.core.metrics import get_metrics, MetricsCollector

__all__ = [
    "logger",
    "configure_logging",
    "ToolType",
    "ToolResult",
    "Message",
    "CitationManager",
    "LRUCache",
    "PersistentEmbeddingCache",
    "get_metrics",
    "MetricsCollector",
]
