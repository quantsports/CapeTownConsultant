"""
Workers package
Multi-agent orchestration with domain-specific workers
"""
from src.orchestration.models import TaskPriority
from src.workers.templates import WorkerTemplates
from src.workers.context_store import SharedContextStore
from src.workers.worker import BaseWorker, WorkerResult
from src.workers.orchestrator import WorkerOrchestrator
from src.workers.templates import WorkerType

__all__ = [
    "WorkerOrchestrator",
    "BaseWorker",
    "WorkerResult",
    "SharedContextStore",
    "WorkerTemplates",
    "TaskPriority",
    "WorkerType"
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