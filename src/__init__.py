"""
CapeTownConsultant - Autonomous Personal Assistant
Modular architecture for production deployment
"""

__version__ = "3.0.0"
__author__ = "CapeTownConsultant Team"

__all__ = ["AutonomousAssistant", "config"]

# Lazy attribute access to avoid circular imports while preserving public API
# PEP 562: module-level __getattr__ is supported in Python 3.7+
def __getattr__(name):
    if name == "AutonomousAssistant":
        from src.interface.assistant import AutonomousAssistant
        return AutonomousAssistant
    if name == "Config":
        from src.config.settings import Config
        return Config
    raise AttributeError(f"module 'src' has no attribute {name!r}")