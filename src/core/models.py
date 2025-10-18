"""
Core data models and enums
Shared types used across the application
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Literal
from enum import Enum


class ToolType(str, Enum):
    """Available tool types"""
    WEB_SEARCH = "web_search"
    PERPLEXITY_SEARCH = "perplexity_search"
    GOOGLE_SEARCH = "google_search"
    KAGI_SEARCH = "kagi_search"
    WIKI_FETCH = "wiki_fetch"
    MEMORY_QUERY = "memory_query"
    MEMORY_UPSERT = "memory_upsert"
    PROFILE_READ = "profile_read"
    PROFILE_WRITE = "profile_write"


@dataclass
class ToolResult:
    """Result from tool execution"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    citations: List[str] = field(default_factory=list)
    source: Optional[str] = None
    cost: float = 0.0


@dataclass
class Message:
    """Chat message with metadata"""
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


class CitationManager:
    """Manage citations for responses"""

    def __init__(self):
        self.citations: List[str] = []
        self.citation_map: Dict[str, int] = {}

    def add_citation(self, url: str) -> int:
        """Add a citation and return its reference number"""
        if url in self.citation_map:
            return self.citation_map[url]
        self.citations.append(url)
        ref_num = len(self.citations)
        self.citation_map[url] = ref_num
        return ref_num

    def add_citations(self, urls: List[str]) -> List[int]:
        """Add multiple citations"""
        return [self.add_citation(url) for url in urls]

    def format_citations(self) -> str:
        """Format citations for display"""
        if not self.citations:
            return ""
        section = "\n\n---\n\n**Sources:**\n"
        for i, url in enumerate(self.citations, 1):
            section += f"[{i}] {url}\n"
        return section

    def clear(self):
        """Clear all citations"""
        self.citations.clear()
        self.citation_map.clear()