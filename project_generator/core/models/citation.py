from typing import Dict, List

class CitationManager:
    """Manage citations and sources"""

    def __init__(self):
        self.sources: List[str] = []
        self.citations: Dict[str, List[str]] = {}

    def add_source(self, source: str) -> int:
        """Add source and return 1-based index"""
        if source not in self.sources:
            self.sources.append(source)
        return self.sources.index(source) + 1

    def add_citation(self, claim: str, source: str):
        """Link claim to source"""
        self.citations.setdefault(claim, [])
        if source not in self.citations[claim]:
            self.citations[claim].append(source)

    def get_formatted_sources(self) -> str:
        """Get formatted source list"""
        if not self.sources:
            return ""
        lines = ["## Sources"]
        for i, src in enumerate(self.sources, 1):
            lines.append(f"[{i}] {src}")
        return "\n".join(lines)
