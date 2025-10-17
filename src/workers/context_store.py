"""
Shared context store for worker orchestration
Manages shared state and information across multiple workers
"""

from typing import Dict, List, Any, Optional
from datetime import datetime


class SharedContextStore:
    """Enhanced context store for research orchestration"""

    def __init__(self):
        self.query = ""
        self.user_profile = {}

        # Research-specific context
        self.research_context = {
            "objective": "",
            "question_type": "general",  # factual, analytical, comparative, etc.
            "domain": "general",
            "time_constraints": None,  # e.g., "last 5 years"
            "evidence_requirements": "moderate",  # low, moderate, high
            "depth_level": "comprehensive",  # overview, comprehensive, deep
            "sub_questions": []
        }

        # Evidence tracking
        self.sources = []  # All sources across workers
        self.evidence_map = {}  # Map claims to sources
        self.source_credibility = {}  # Source -> credibility score

        # Worker coordination
        self.worker_insights = []
        self.worker_priorities = {}
        self.tool_results = {}
        self.synthesis = {}

        # Quality metrics
        self.confidence_scores = {}
        self.identified_gaps = []
        self.conflicting_info = []

        # Variables for template substitution
        self.variables = {}

    @staticmethod
    def validate_namespace(namespace: str) -> bool:
        """
        Validate namespace format for Pinecone compatibility

        Args:
            namespace: Namespace string to validate

        Returns:
            True if valid, False otherwise
        """
        if not namespace or not isinstance(namespace, str):
            return False

        # Pinecone namespace requirements
        if len(namespace) > 512:
            return False

        # Check for valid characters (alphanumeric, hyphens, underscores, colons)
        import re
        if not re.match(r'^[a-zA-Z0-9_:-]+$', namespace):
            return False

        return True

    @staticmethod
    def sanitize_user_id(user_id: str) -> str:
        """
        Sanitize user_id for use as namespace

        Args:
            user_id: Raw user identifier

        Returns:
            Sanitized user_id safe for namespace use
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")

        # Remove whitespace and replace spaces with underscores
        safe_id = user_id.strip().replace(" ", "_")

        if not safe_id:
            raise ValueError("user_id cannot be empty after sanitization")

        # Remove invalid characters
        import re
        safe_id = re.sub(r'[^a-zA-Z0-9_:-]', '', safe_id)

        if not safe_id:
            raise ValueError("user_id contains no valid characters")

        # Truncate if too long
        if len(safe_id) > 500:  # Leave room for prefix like "user:"
            safe_id = safe_id[:500]

        return safe_id

    def initialize(self, query: str, user_profile: Dict):
        """Initialize context with query and user profile"""
        self.query = query
        self.user_profile = user_profile
        self.variables = {
            "query": query,
            "user_profile": str(user_profile) if user_profile else "No profile available",
            "additional_context": ""
        }

    def add_source(self, source: str, credibility: float = 0.5, worker_type: str = ""):
        """Track source with credibility score"""
        if source not in self.sources:
            self.sources.append(source)
            self.source_credibility[source] = credibility

    def add_evidence(self, claim: str, sources: List[str], confidence: float, worker: str = ""):
        """Map claim to supporting sources"""
        self.evidence_map[claim] = {
            "sources": sources,
            "confidence": confidence,
            "worker": worker
        }

    def identify_conflict(self, claim1: str, claim2: str, explanation: str):
        """Track conflicting information"""
        self.conflicting_info.append({
            "claim1": claim1,
            "claim2": claim2,
            "explanation": explanation,
            "timestamp": datetime.now().isoformat()
        })

    def add_worker_insight(self, worker_type: str, insight: Dict):
        """Add insight from a worker"""
        self.worker_insights.append({
            "worker_type": worker_type,
            "insight": insight,
            "timestamp": datetime.now().isoformat()
        })

    def store_tool_result(self, tool_name: str, result: Any):
        """Store tool execution result"""
        if tool_name not in self.tool_results:
            self.tool_results[tool_name] = []

        self.tool_results[tool_name].append({
            "result": result,
            "timestamp": datetime.now().isoformat()
        })

    def add_tool_result(self, tool_name: str, result: Any):
        """
        Add tool result (alias for store_tool_result for backward compatibility)

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
        sources: List[str]
    ):
        """
        Add worker contribution to shared context

        Args:
            worker_type: Type of worker making contribution
            data: Data/findings from the worker
            confidence: Confidence score (0.0-1.0)
            sources: List of sources used
        """
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
        other_insights = self._get_other_worker_insights(worker_type)

        return {
            "query": self.query,
            "user_profile": self.user_profile,
            "research_context": self.research_context,
            "prior_insights": other_insights,
            "other_worker_insights": other_insights,  # Alias for compatibility
            "tool_results": self.tool_results,
            "sources_found": len(self.sources)
        }

    def _get_other_worker_insights(self, current_worker: str) -> List[Dict]:
        """Get insights from other workers"""
        return [
            insight for insight in self.worker_insights
            if insight["worker_type"] != current_worker
        ]

    def get_variable_dict(self) -> Dict[str, str]:
        """Get variables for template substitution"""
        return {
            "query": self.query,
            "user_profile": str(self.user_profile) if self.user_profile else "",
            "additional_context": self._format_additional_context(),
            "time_constraints": str(self.research_context.get("time_constraints", ""))
        }

    def _format_additional_context(self) -> str:
        """Format additional context from accumulated information"""
        context_parts = []

        if self.worker_insights:
            context_parts.append(f"Prior worker findings: {len(self.worker_insights)} insights gathered")

        if self.sources:
            context_parts.append(f"Sources consulted: {len(self.sources)}")

        if self.conflicting_info:
            context_parts.append(f"Conflicting information identified: {len(self.conflicting_info)} conflicts")

        return "; ".join(context_parts) if context_parts else "No additional context"

    def get_research_summary(self) -> Dict:
        """Get comprehensive research summary"""
        avg_credibility = 0.0
        if self.source_credibility:
            avg_credibility = sum(self.source_credibility.values()) / len(self.source_credibility)

        return {
            "query": self.query,
            "context": self.research_context,
            "sources_count": len(self.sources),
            "avg_credibility": avg_credibility,
            "evidence_count": len(self.evidence_map),
            "conflicts_found": len(self.conflicting_info),
            "gaps_identified": self.identified_gaps,
            "worker_insights_count": len(self.worker_insights)
        }

    def add_gap(self, gap_description: str):
        """Add identified research gap"""
        self.identified_gaps.append({
            "description": gap_description,
            "timestamp": datetime.now().isoformat()
        })

    def update_research_context(self, updates: Dict):
        """Update research context with new information"""
        self.research_context.update(updates)