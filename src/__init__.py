"""
CapeTownConsultant - Autonomous Personal Assistant
Modular architecture for production deployment
"""

__version__ = "3.0.0"
__author__ = "CapeTownConsultant Team"

from src.interface.assistant import AutonomousAssistant
from src.config.settings import Config

__all__ = ["AutonomousAssistant", "Config"]