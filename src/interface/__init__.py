"""
Interface package
User-facing interfaces (CLI, API, etc.)
"""

__all__ = ["AutonomousAssistant", "run_cli", "main"]

# Lazy attribute access to avoid circular imports
# PEP 562: module-level __getattr__ is supported in Python 3.7+
def __getattr__(name):
    if name == "AutonomousAssistant":
        from .assistant import AutonomousAssistant
        return AutonomousAssistant
    if name in ("run_cli", "main"):
        from .cli import run_cli, main
        return {"run_cli": run_cli, "main": main}[name]
    raise AttributeError(f"module 'src.interface' has no attribute {name!r}")