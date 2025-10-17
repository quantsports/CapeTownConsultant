from dataclasses import dataclass
from typing import Any, List, Optional

@dataclass
class Message:
    """Chat message"""
    role: str
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Any]] = None
    tool_call_id: Optional[str] = None
