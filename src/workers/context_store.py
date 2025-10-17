"""
Shared context store for multi-agent orchestration
Enables workers to share information and build on each other's work
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
import json


@dataclass
class WorkerContribution:
    """A contribution from a worker to shared context"""
    worker_type: str
    timestamp: datetime
    data: Dict[str, Any]
    confidence: float = 1.0
    sources: List[str] = field(default_factory=list)


class SharedContextStore:
    """
    Centralized context storage accessible to all workers
    Enables information sharing and collaborative problem-solving
    """

    def __init__(self):
        self.context: Dict[str, Any] = {
            "user_profile": {},
            "query": "",
            "parsed_query": {},
            "worker_contributions": [],
            "tool_results": {},
            "synthesis": {},
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        }

    def initialize(
            self,
            query: str,
            user_profile: Dict[str, Any],
            parsed_query: Optional[Dict[str, Any]] = None
    ):
        """Initialize context with query and user info"""
        self.context["query"] = query
        self.context["user_profile"] = user_profile
        self.context["parsed_query"] = parsed_query or self._parse_query(query)
        self.context["metadata"]["updated_at"] = datetime.now().isoformat()

    def _parse_query(self, query: str) -> Dict[str, Any]:
        """Extract structured information from query"""
        query_lower = query.lower()

        # Extract intent keywords
        intent_keywords = {
            "analyze": ["analyze", "analysis", "examine", "evaluate"],
            "plan": ["plan", "design", "create", "develop"],
            "improve": ["improve", "optimize", "enhance", "increase"],
            "reduce": ["reduce", "decrease", "cut", "lower"],
            "advice": ["advice", "help", "suggest", "recommend"]
        }

        detected_intents = []
        for intent, keywords in intent_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                detected_intents.append(intent)

        # Extract numbers (could be costs, percentages, etc.)
        import re
        numbers = re.findall(r'\$?(\d+(?:,\d{3})*(?:\.\d+)?)\s*%?', query)

        # Extract time references
        time_keywords = ["today", "this week", "this month", "this year",
                         "next week", "next month", "quarterly", "annually"]
        time_refs = [kw for kw in time_keywords if kw in query_lower]

        return {
            "intents": detected_intents,
            "numbers": numbers,
            "time_references": time_refs,
            "length": len(query),
            "complexity": "high" if len(query) > 100 else "medium" if len(query) > 50 else "low"
        }

    def add_contribution(
            self,
            worker_type: str,
            data: Dict[str, Any],
            confidence: float = 1.0,
            sources: List[str] = None
    ):
        """Add a worker's contribution to shared context"""
        contribution = WorkerContribution(
            worker_type=worker_type,
            timestamp=datetime.now(),
            data=data,
            confidence=confidence,
            sources=sources or []
        )

        self.context["worker_contributions"].append(contribution)
        self.context["metadata"]["updated_at"] = datetime.now().isoformat()

    def add_tool_result(self, tool_name: str, result: Any):
        """Store a tool execution result"""
        if tool_name not in self.context["tool_results"]:
            self.context["tool_results"][tool_name] = []

        self.context["tool_results"][tool_name].append({
            "result": result,
            "timestamp": datetime.now().isoformat()
        })

    def get_relevant_context(self, worker_type: str) -> Dict[str, Any]:
        """Get context relevant to a specific worker"""
        # Base context
        relevant = {"query": self.context["query"], "user_profile": self.context["user_profile"],
                    "parsed_query": self.context["parsed_query"], "other_worker_insights": []}

        # Add contributions from other workers that might be relevant
        for contrib in self.context["worker_contributions"]:
            if contrib.worker_type != worker_type:
                relevant["other_worker_insights"].append({
                    "from_worker": contrib.worker_type,
                    "summary": self._summarize_contribution(contrib.data),
                    "confidence": contrib.confidence
                })

        return relevant

    def _summarize_contribution(self, data: Dict[str, Any]) -> str:
        """Create a brief summary of a contribution"""
        # Extract key points
        summary_parts = []

        if "recommendations" in data:
            summary_parts.append(f"Recommended: {len(data['recommendations'])} items")

        if "analysis" in data:
            summary_parts.append("Provided analysis")

        if "findings" in data:
            summary_parts.append(f"Found {len(data.get('findings', []))} key points")

        return "; ".join(summary_parts) if summary_parts else "Provided insights"

    def get_all_contributions(self) -> List[WorkerContribution]:
        """Get all worker contributions"""
        return self.context["worker_contributions"]

    def set_synthesis(self, synthesis: Dict[str, Any]):
        """Store the final synthesized result"""
        self.context["synthesis"] = synthesis
        self.context["metadata"]["updated_at"] = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Export context as dictionary"""
        # Convert WorkerContribution objects to dicts
        exported = self.context.copy()
        exported["worker_contributions"] = [
            {
                "worker_type": c.worker_type,
                "timestamp": c.timestamp.isoformat(),
                "data": c.data,
                "confidence": c.confidence,
                "sources": c.sources
            }
            for c in self.context["worker_contributions"]
        ]
        return exported

    def to_json(self) -> str:
        """Export context as JSON"""
        return json.dumps(self.to_dict(), indent=2, default=str)

    def get_summary(self) -> str:
        """Get a human-readable summary of the context"""
        lines = [
            f"Query: {self.context['query'][:100]}...",
            f"Workers engaged: {len(self.context['worker_contributions'])}",
            f"Tools used: {', '.join(self.context['tool_results'].keys())}",
            f"Updated: {self.context['metadata']['updated_at']}"
        ]
        return "\n".join(lines)

    def get_variable_dict(self, additional_vars: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Generate a dictionary for template variable substitution

        Returns:
            Dictionary with keys matching template variables
        """
        profile_str = json.dumps(self.context["user_profile"], indent=2) if self.context[
            "user_profile"] else "No profile data"

        # Build additional context from other workers
        additional_context_parts = []
        for contrib in self.context["worker_contributions"]:
            summary = self._summarize_contribution(contrib.data)
            additional_context_parts.append(f"- {contrib.worker_type}: {summary}")

        additional_context = "\n".join(additional_context_parts) if additional_context_parts else ""

        variables = {
            "query": self.context["query"],
            "user_profile": profile_str,
            "additional_context": additional_context
        }

        # Add any custom variables
        if additional_vars:
            variables.update(additional_vars)

        return variables

    def clear(self):
        """Clear all context data"""
        self.__init__()