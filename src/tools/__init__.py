"""
CapeTownConsultant - Autonomous Personal Assistant
Modular architecture with multi-agent orchestration
"""

__version__ = "3.1.0"
__author__ = "CapeTownConsultant Team"

__all__ = [
    "AutonomousAssistant",
    "Config",
    "WorkerOrchestrator",
    "WorkerType",
    "WorkerTemplates"
]

# Lazy exports to avoid circular imports
# PEP 562: module-level __getattr__ is supported in Python 3.7+
def __getattr__(name):
    if name == "AutonomousAssistant":
        from src.interface.assistant import AutonomousAssistant
        return AutonomousAssistant
    if name == "Config":
        from src.config.settings import Config
        return Config
    if name == "WorkerOrchestrator":
        from src.workers.orchestrator import WorkerOrchestrator
        return WorkerOrchestrator
    if name in ("WorkerType", "WorkerTemplates"):
        from src.workers.templates import WorkerType, WorkerTemplates
        return {"WorkerType": WorkerType, "WorkerTemplates": WorkerTemplates}[name]
    raise AttributeError(f"module 'src.tools' has no attribute {name!r}")