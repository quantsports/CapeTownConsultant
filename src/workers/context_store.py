"""
Shared context store for worker orchestration
FIXES: High #4 - Unbounded cache growth in tool_results
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import OrderedDict
from dataclasses import dataclass, field

from src.core.logging import logger


@dataclass
class WorkerContribution:
    """Represents a worker's contribution to the shared context"""
    worker_type: str
    data: Dict[str, Any]
    confidence: float
    sources: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class SharedContextStore:
    """
    Centralized context store for worker orchestration
    HIGH FIX #4: Enforce bounded cache for tool_results with FIFO eviction
    """

    def __init__(self, max_tool_results: int = 100):
        """
        Initialize shared context store

        Args:
            max_tool_results: Maximum number of tool results to cache (default: 100)
        """
        self.context: Dict[str, Any] = {
            "query": "",
            "user_profile": {},
            "parsed_query": {},
            "worker_contributions": [],
            "synthesis": {},
        }

        # HIGH FIX #4: Use OrderedDict with max size for FIFO eviction
        self.max_tool_results = max_tool_results
        self.tool_results: OrderedDict[str, Any] = OrderedDict()

        self.confidence_scores: Dict[str, float] = {}
        self.sources: List[Dict[str, Any]] = []

        logger.debug("context_store_initialized", max_tool_results=max_tool_results)

    def initialize(
        self,
        query: str,
        user_profile: Optional[Dict] = None,
        additional_context: Optional[Dict] = None
    ):
        """Initialize context with query and user profile"""
        self.context["query"] = query
        self.context["user_profile"] = user_profile or {}

        # Parse query for intents and complexity
        self.context["parsed_query"] = self._parse_query(query)

        # Add additional context if provided
        if additional_context:
            self.context.update(additional_context)

        logger.info("context_initialized", query_length=len(query))

    def _parse_query(self, query: str) -> Dict:
        """Parse query to extract intents and complexity"""
        query_lower = query.lower()

        # Simple intent detection
        intents = []
        if any(word in query_lower for word in ["analyze", "analysis", "compare"]):
            intents.append("analysis")
        if any(word in query_lower for word in ["design", "create", "plan"]):
            intents.append("creation")
        if any(word in query_lower for word in ["cost", "budget", "price"]):
            intents.append("financial")
        if any(word in query_lower for word in ["market", "strategy", "competition"]):
            intents.append("strategic")

        # Determine complexity
        word_count = len(query.split())
        complexity = "simple" if word_count < 10 else "moderate" if word_count < 20 else "complex"

        return {
            "intents": intents,
            "word_count": word_count,
            "complexity": complexity,
            "questions": query.count("?"),
        }

    def store_tool_result(self, tool_name: str, result: Any):
        """
        Store tool execution result
        HIGH FIX #4: Enforce max size with FIFO eviction
        """
        # HIGH FIX #4: If at capacity, remove oldest entry (FIFO)
        if len(self.tool_results) >= self.max_tool_results:
            oldest_key = next(iter(self.tool_results))
            removed = self.tool_results.pop(oldest_key)
            logger.debug(
                "tool_result_evicted",
                tool=oldest_key,
                current_size=len(self.tool_results)
            )

        # Add new entry
        timestamp = datetime.now().isoformat()
        key = f"{tool_name}:{timestamp}"
        self.tool_results[key] = {
            "tool": tool_name,
            "result": result,
            "timestamp": timestamp
        }

        logger.debug(
            "tool_result_stored",
            tool=tool_name,
            cache_size=len(self.tool_results),
            max_size=self.max_tool_results
        )

    def add_worker_insight(self, worker_type: str, insight: Dict):
        """Add worker insight to context"""
        self.context.setdefault("worker_insights", []).append({
            "worker": worker_type,
            "insight": insight,
            "timestamp": datetime.now().isoformat()
        })

    def add_source(
        self,
        url: str,
        credibility: float = 0.8,
        worker_type: Optional[str] = None
    ):
        """Add a source with credibility score"""
        source = {
            "url": url,
            "credibility": credibility,
            "timestamp": datetime.now().isoformat()
        }
        if worker_type:
            source["discovered_by"] = worker_type

        # Avoid duplicates
        if not any(s["url"] == url for s in self.sources):
            self.sources.append(source)

    def get_tool_result(self, tool_name: str) -> Optional[Any]:
        """Get most recent result for a specific tool"""
        # Search in reverse order (most recent first)
        for key, value in reversed(self.tool_results.items()):
            if value["tool"] == tool_name:
                return value["result"]
        return None

    def get_all_tool_results(self) -> List[Dict]:
        """Get all tool results"""
        return list(self.tool_results.values())

    def add_tool_result(self, tool_name: str, result: Any):
        """
        Store tool execution result (alias for store_tool_result)

        Args:
            tool_name: Name of the tool executed
            result: Tool execution result
        """
        self.store_tool_result(tool_name, result)

    def record_tool_execution(self, tool_name: str, result: Any):
        """
        Record tool execution (legacy method for backward compatibility)
        Delegates to store_tool_result

        Args:
            tool_name: Name of the tool executed
            result: Tool execution result
        """
        self.store_tool_result(tool_name, result)

    def add_contribution(
        self,
        worker_type: str,
        data: Dict[str, Any],
        confidence: float,
        sources: List[str] = None
    ):
        """
        Add worker contribution to shared context

        Args:
            worker_type: Type of worker making contribution
            data: Data/findings from the worker
            confidence: Confidence score (0.0-1.0)
            sources: List of sources used
        """
        sources = sources or []

        # Store as worker insight
        self.add_worker_insight(worker_type, {
            "data": data,
            "confidence": confidence,
            "sources": sources
        })

        # Update confidence scores
        self.confidence_scores[worker_type] = confidence

        # Add sources with credibility based on confidence
        for source in sources:
            self.add_source(source, credibility=confidence, worker_type=worker_type)

        logger.debug(
            "contribution_added",
            worker=worker_type,
            confidence=confidence,
            sources_count=len(sources)
        )

    def set_synthesis(self, synthesis: Dict):
        """Store final synthesis"""
        self.synthesis = synthesis
        self.synthesis["timestamp"] = datetime.now().isoformat()

    def get_relevant_context(self, worker_type: str) -> Dict:
        """
        Get relevant context for a specific worker

        Returns both 'prior_insights' and 'other_worker_insights' keys
        for backward compatibility with different worker implementations.
        """
        other_insights = [
            insight for insight in self.context.get("worker_insights", [])
            if insight["worker"] != worker_type
        ]

        return {
            "query": self.context["query"],
            "user_profile": self.context["user_profile"],
            "parsed_query": self.context["parsed_query"],
            "other_worker_insights": other_insights,
            "prior_insights": other_insights,  # Alias for compatibility
            "available_sources": self.sources,
            "tool_results": list(self.tool_results.values())  # Include cached tool results
        }

    def get_all_contributions(self) -> List[WorkerContribution]:
        """Get all worker contributions"""
        contributions = []
        for insight in self.context.get("worker_insights", []):
            contributions.append(WorkerContribution(
                worker_type=insight["worker"],
                data=insight["insight"],
                confidence=self.confidence_scores.get(insight["worker"], 0.5),
                sources=[],
                timestamp=insight["timestamp"]
            ))
        return contributions

    def get_variable_dict(self) -> Dict[str, str]:
        """Generate variables for template substitution"""
        return {
            "query": self.context["query"],
            "user_profile": str(self.context["user_profile"]),
            "parsed_intents": ", ".join(self.context["parsed_query"].get("intents", [])),
            "complexity": self.context["parsed_query"].get("complexity", "moderate"),
            "prior_insights": str(self.context.get("worker_insights", [])),
            "additional_context": str(self.context.get("additional_context", {}))
        }

    def validate(self) -> bool:
        """Validate context store state"""
        try:
            # Check required fields
            if not self.context.get("query"):
                logger.warning("context_validation_failed", reason="missing_query")
                return False

            # Check tool results size
            if len(self.tool_results) > self.max_tool_results:
                logger.error(
                    "context_validation_failed",
                    reason="tool_results_exceeded_max",
                    current=len(self.tool_results),
                    max=self.max_tool_results
                )
                return False

            return True

        except Exception as e:
            logger.error("context_validation_error", error=str(e))
            return False

    def get_stats(self) -> Dict:
        """Get context store statistics"""
        return {
            "query_length": len(self.context["query"]),
            "worker_count": len(self.context.get("worker_insights", [])),
            "tool_results_count": len(self.tool_results),
            "tool_results_max": self.max_tool_results,
            "sources_count": len(self.sources),
            "has_synthesis": bool(self.synthesis),
            "profile_keys": len(self.context["user_profile"]),
        }