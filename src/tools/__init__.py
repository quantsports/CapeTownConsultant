"""
Tools Module - Tool execution and validation
Provides tool executor, schemas, and type definitions
"""
from src.core import ToolType, ToolResult
from src.tools.executor import ToolExecutor
from src.tools.schemas import ToolSchemas

__all__ = [
    "ToolExecutor",
    "ToolSchemas",
    "ToolType",
    "ToolResult"
]


# Lazy exports to avoid circular imports
# PEP 562: module-level __getattr__ is supported in Python 3.7+
def __getattr__(name: str):
    if name == "ToolExecutor":
        from src.tools.executor import ToolExecutor
        return ToolExecutor
    if name == "ToolSchemas":
        from src.tools.schemas import ToolSchemas
        return ToolSchemas
    if name in ("ToolType", "ToolResult"):
        from src.core.models import ToolType, ToolResult
        return {"ToolType": ToolType, "ToolResult": ToolResult}[name]
    raise AttributeError(f"module '{__name__}' has no attribute {name!r}")
