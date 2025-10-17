"""
Core data models public surface.
Keeps backward compatibility with:
    from src.core.models import ToolType, ToolResult, Message, CitationManager
"""
from .tool_types import ToolType
from .tool_result import ToolResult
from .messaging import Message
from .citation import CitationManager

__all__ = ["ToolType", "ToolResult", "Message", "CitationManager"]
