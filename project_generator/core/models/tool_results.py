from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class ToolResult:
    """Result from tool execution"""
    tool_name: str
    success: bool
    data: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    sources: List[str] = field(default_factory=list)
