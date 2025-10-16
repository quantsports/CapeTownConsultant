"""
Workers package
Multi-agent orchestration with domain-specific workers
"""

__all__ = [
    "WorkerOrchestrator",
    "BaseWorker",
    "WorkerResult",
    "SharedContextStore",
    "WorkerTemplates"
]

# Lazy exports to avoid circular imports
# PEP 562: module-level __getattr__ is supported in Python 3.7+
def __getattr__(name):
    if name == "WorkerOrchestrator":
        from .orchestrator import WorkerOrchestrator
        return WorkerOrchestrator
    if name in ("BaseWorker", "WorkerResult"):
        from .worker import BaseWorker, WorkerResult
        return {"BaseWorker": BaseWorker, "WorkerResult": WorkerResult}[name]
    if name == "SharedContextStore":
        from .context_store import SharedContextStore
        return SharedContextStore
    if name == "WorkerTemplates":
        from .templates import WorkerTemplates
        return WorkerTemplates
    raise AttributeError(f"module 'src.workers' has no attribute {name!r}")