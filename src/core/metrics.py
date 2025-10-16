"""
Lightweight metrics collection service
- Logs to terminal and to log file via existing structured logger
- Tracks average response times, cache hit rates, and tool usage distribution
"""
from __future__ import annotations

import time
import threading
from typing import Dict, Optional

from src.config.settings import Config
from src.core.logging import logger


class MetricsCollector:
    """In-process metrics collector with simple aggregation.

    Notes:
    - Designed to be lightweight and have zero external dependencies.
    - Uses the existing logger sinks: console + file (app.log).
    - Safe to import in tests; can be disabled via Config.METRICS_ENABLED.
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        # Locks for thread-safety where code may run in threads
        self._lock = threading.Lock()
        self._response_times: Dict[str, Dict[str, float]] = {}
        # {service: {"count": int, "total_ms": float, "avg_ms": float, "last_ms": float}}
        self._cache_stats: Dict[str, Dict[str, float]] = {}
        # {cache_name: {"hits": int, "misses": int, "hit_rate": float}}
        self._tool_usage: Dict[str, int] = {}

    def record_response_time(self, service: str, duration_ms: float):
        if not self.enabled:
            return
        with self._lock:
            stats = self._response_times.setdefault(service, {
                "count": 0,
                "total_ms": 0.0,
                "avg_ms": 0.0,
                "last_ms": 0.0,
            })
            stats["count"] += 1
            stats["total_ms"] += float(duration_ms)
            stats["last_ms"] = float(duration_ms)
            stats["avg_ms"] = stats["total_ms"] / stats["count"]
            # Emit a structured metrics log line
            logger.info(
                "metrics_response_time",
                service=service,
                duration_ms=round(duration_ms, 3),
                avg_ms=round(stats["avg_ms"], 3),
                count=int(stats["count"]),
            )

    def record_cache_access(self, cache_name: str, hit: bool):
        if not self.enabled:
            return
        with self._lock:
            stats = self._cache_stats.setdefault(cache_name, {
                "hits": 0,
                "misses": 0,
                "hit_rate": 0.0,
            })
            if hit:
                stats["hits"] += 1
            else:
                stats["misses"] += 1
            total = stats["hits"] + stats["misses"]
            stats["hit_rate"] = (stats["hits"] / total) if total > 0 else 0.0
            logger.info(
                "metrics_cache",
                cache=cache_name,
                hit=hit,
                hits=int(stats["hits"]),
                misses=int(stats["misses"]),
                hit_rate=round(stats["hit_rate"], 4),
            )

    def record_tool_usage(self, tool_name: str):
        if not self.enabled:
            return
        with self._lock:
            self._tool_usage[tool_name] = self._tool_usage.get(tool_name, 0) + 1
            logger.info(
                "metrics_tool_usage",
                tool=tool_name,
                count=int(self._tool_usage[tool_name]),
            )

    def snapshot(self) -> Dict:
        """Return a copy of current metrics state for debugging/tests."""
        with self._lock:
            return {
                "response_times": {k: dict(v) for k, v in self._response_times.items()},
                "cache": {k: dict(v) for k, v in self._cache_stats.items()},
                "tool_usage": dict(self._tool_usage),
            }


# Singleton holder
_metrics_singleton: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    global _metrics_singleton
    if _metrics_singleton is None:
        _metrics_singleton = MetricsCollector(enabled=getattr(Config, "METRICS_ENABLED", True))
    return _metrics_singleton
