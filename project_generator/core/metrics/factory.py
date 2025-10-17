from typing import Optional

from src.core.metrics.collector import MetricsCollector

_metrics_instance: Optional[MetricsCollector] = None

def get_metrics() -> MetricsCollector:
    """Singleton-style accessor honoring Config.METRICS_ENABLED."""
    global _metrics_instance
    if _metrics_instance is None:
        from src.config.settings import Config
        _metrics_instance = MetricsCollector(enabled=Config.METRICS_ENABLED)
    return _metrics_instance
