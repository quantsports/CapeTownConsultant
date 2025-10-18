"""
Memory Viewer
View, search, and manage stored memories
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import json
from enum import Enum

from src.memory.vector import VectorMemory
from src.memory.profile import ProfileManager
from src.core.logging import logger
from src.core.models import ToolResult


class MemoryType(Enum):
    """Types of memories"""

    VECTOR = "vector"
    PROFILE = "profile"
    ALL = "all"


class SortOrder(Enum):
    """Sort orders for memory listing"""

    NEWEST_FIRST = "newest"
    OLDEST_FIRST = "oldest"
    HIGHEST_SCORE = "score_desc"
    LOWEST_SCORE = "score_asc"


class MemoryViewer:
    """View and manage stored memories"""

    def __init__(self, vector_memory: VectorMemory, profile_manager: ProfileManager):
        self.vector_memory = vector_memory
        self.profile_manager = profile_manager

    async def list_vector_memories(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        sort_by: SortOrder = SortOrder.NEWEST_FIRST,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_score: Optional[float] = None,
    ) -> ToolResult:
        """
        List vector memories with pagination and filtering

        Args:
            user_id: User identifier
            limit: Maximum number of results
            offset: Number of results to skip
            sort_by: Sort order
            date_from: Filter memories after this date
            date_to: Filter memories before this date
            min_score: Minimum similarity score (for filtered queries)

        Returns:
            ToolResult with memory list
        """
        if not self.vector_memory.is_configured():
            return ToolResult(success=False, error="Vector memory not configured")

        try:
            namespace = f"user:{user_id}"

            # Use a broad query to fetch all memories
            # We query with a generic embedding to get all vectors
            broad_query = "user information preferences facts"
            query_result = await self.vector_memory.query(
                text=broad_query,
                namespace=namespace,
                top_k=min(limit * 3, 1000),  # Fetch more for filtering
                user_id=user_id,
            )

            if not query_result.success:
                return query_result

            memories = query_result.data.get("matches", [])

            # Apply filters
            filtered_memories = self._apply_filters(
                memories, date_from=date_from, date_to=date_to, min_score=min_score
            )

            # Sort memories
            sorted_memories = self._sort_memories(filtered_memories, sort_by)

            # Apply pagination
            start_idx = offset
            end_idx = offset + limit
            paginated_memories = sorted_memories[start_idx:end_idx]

            # Format for display
            formatted_memories = []
            for i, memory in enumerate(paginated_memories, start=offset + 1):
                formatted_memories.append(
                    {
                        "index": i,
                        "id": memory.get("id", ""),
                        "text": memory.get("text", ""),
                        "score": memory.get("score", 0.0),
                        "timestamp": memory.get("timestamp", ""),
                        "metadata": memory.get("metadata", {}),
                    }
                )

            return ToolResult(
                success=True,
                data={
                    "memories": formatted_memories,
                    "total_count": len(filtered_memories),
                    "displayed_count": len(paginated_memories),
                    "offset": offset,
                    "limit": limit,
                    "namespace": namespace,
                },
            )

        except Exception as e:
            logger.error("list_memories_failed", error=str(e), user_id=user_id)
            return ToolResult(success=False, error=f"Failed to list memories: {str(e)}")

    async def search_memories(
        self, user_id: str, query: str, top_k: int = 20, min_score: float = 0.7
    ) -> ToolResult:
        """
        Search memories semantically

        Args:
            user_id: User identifier
            query: Search query
            top_k: Number of results
            min_score: Minimum similarity threshold

        Returns:
            ToolResult with matching memories
        """
        if not self.vector_memory.is_configured():
            return ToolResult(success=False, error="Vector memory not configured")

        try:
            namespace = f"user:{user_id}"

            result = await self.vector_memory.query(
                text=query, namespace=namespace, top_k=top_k, user_id=user_id
            )

            if not result.success:
                return result

            # Filter by minimum score
            matches = result.data.get("matches", [])
            filtered_matches = [m for m in matches if m.get("score", 0.0) >= min_score]

            formatted_results = []
            for i, match in enumerate(filtered_matches, 1):
                formatted_results.append(
                    {
                        "rank": i,
                        "id": match.get("id", ""),
                        "text": match.get("text", ""),
                        "score": match.get("score", 0.0),
                        "relevance": self._score_to_relevance(match.get("score", 0.0)),
                        "timestamp": match.get("timestamp", ""),
                        "metadata": match.get("metadata", {}),
                    }
                )

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "results": formatted_results,
                    "result_count": len(formatted_results),
                    "namespace": namespace,
                },
            )

        except Exception as e:
            logger.error("search_memories_failed", error=str(e), user_id=user_id)
            return ToolResult(
                success=False, error=f"Failed to search memories: {str(e)}"
            )

    async def get_profile(self, user_id: str) -> ToolResult:
        """
        Get complete user profile

        Args:
            user_id: User identifier

        Returns:
            ToolResult with profile data
        """
        try:
            profile = await self.profile_manager.read(user_id)

            # Add metadata
            profile_info = {
                "user_id": user_id,
                "profile_data": profile,
                "field_count": len(profile),
                "fields": list(profile.keys()),
            }

            return ToolResult(success=True, data=profile_info)

        except Exception as e:
            logger.error("get_profile_failed", error=str(e), user_id=user_id)
            return ToolResult(success=False, error=f"Failed to get profile: {str(e)}")

    async def get_memory_stats(self, user_id: str) -> ToolResult:
        """
        Get statistics about stored memories

        Args:
            user_id: User identifier

        Returns:
            ToolResult with memory statistics
        """
        try:
            stats = {
                "user_id": user_id,
                "vector_memory_configured": self.vector_memory.is_configured(),
                "profile_exists": False,
                "memory_stats": {},
            }

            # Get profile info
            profile = await self.profile_manager.read(user_id)
            if profile:
                stats["profile_exists"] = True
                stats["profile_field_count"] = len(profile)

            # Get vector memory count (approximate)
            if self.vector_memory.is_configured():
                namespace = f"user:{user_id}"

                # Query broadly to estimate count
                result = await self.vector_memory.query(
                    text="all user information",
                    namespace=namespace,
                    top_k=1000,
                    user_id=user_id,
                )

                if result.success:
                    memories = result.data.get("matches", [])
                    stats["memory_stats"] = {
                        "approximate_count": len(memories),
                        "namespace": namespace,
                    }

                    # Get date range
                    if memories:
                        timestamps = [
                            m.get("timestamp", "")
                            for m in memories
                            if m.get("timestamp")
                        ]
                        if timestamps:
                            timestamps.sort()
                            stats["memory_stats"]["oldest_memory"] = timestamps[0]
                            stats["memory_stats"]["newest_memory"] = timestamps[-1]

            return ToolResult(success=True, data=stats)

        except Exception as e:
            logger.error("get_memory_stats_failed", error=str(e), user_id=user_id)
            return ToolResult(
                success=False, error=f"Failed to get memory stats: {str(e)}"
            )

    async def delete_memory(self, user_id: str, memory_id: str) -> ToolResult:
        """
        Delete a specific memory

        Args:
            user_id: User identifier
            memory_id: Memory vector ID to delete

        Returns:
            ToolResult with deletion status
        """
        if not self.vector_memory.is_configured():
            return ToolResult(success=False, error="Vector memory not configured")

        try:
            namespace = f"user:{user_id}"

            # Delete from Pinecone
            self.vector_memory.index.delete(ids=[memory_id], namespace=namespace)

            logger.info(
                "memory_deleted",
                user_id=user_id,
                memory_id=memory_id,
                namespace=namespace,
            )

            return ToolResult(
                success=True,
                data={"deleted": True, "memory_id": memory_id, "namespace": namespace},
            )

        except Exception as e:
            logger.error("delete_memory_failed", error=str(e), user_id=user_id)
            return ToolResult(success=False, error=f"Failed to delete memory: {str(e)}")

    async def export_memories(
        self, user_id: str, format: str = "json", include_profile: bool = True
    ) -> ToolResult:
        """
        Export all memories for a user

        Args:
            user_id: User identifier
            format: Export format (json, csv)
            include_profile: Include profile data

        Returns:
            ToolResult with export data
        """
        try:
            export_data = {
                "user_id": user_id,
                "exported_at": datetime.now().isoformat(),
                "memories": [],
                "profile": {},
            }

            # Get all vector memories
            if self.vector_memory.is_configured():
                memories_result = await self.list_vector_memories(
                    user_id=user_id, limit=10000  # Large limit for full export
                )

                if memories_result.success:
                    export_data["memories"] = memories_result.data.get("memories", [])

            # Get profile
            if include_profile:
                profile_result = await self.get_profile(user_id)
                if profile_result.success:
                    export_data["profile"] = profile_result.data.get("profile_data", {})

            # Format based on requested format
            if format == "json":
                formatted_export = json.dumps(export_data, indent=2)
            elif format == "csv":
                formatted_export = self._format_as_csv(export_data)
            else:
                formatted_export = str(export_data)

            return ToolResult(
                success=True,
                data={
                    "format": format,
                    "export": formatted_export,
                    "memory_count": len(export_data["memories"]),
                    "includes_profile": include_profile,
                },
            )

        except Exception as e:
            logger.error("export_memories_failed", error=str(e), user_id=user_id)
            return ToolResult(
                success=False, error=f"Failed to export memories: {str(e)}"
            )

    # Helper methods

    def _apply_filters(
        self,
        memories: List[Dict],
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_score: Optional[float] = None,
    ) -> List[Dict]:
        """Apply filters to memory list"""
        filtered = memories

        if date_from:
            filtered = [
                m
                for m in filtered
                if self._parse_timestamp(m.get("timestamp", "")) >= date_from
            ]

        if date_to:
            filtered = [
                m
                for m in filtered
                if self._parse_timestamp(m.get("timestamp", "")) <= date_to
            ]

        if min_score is not None:
            filtered = [m for m in filtered if m.get("score", 0.0) >= min_score]

        return filtered

    def _sort_memories(self, memories: List[Dict], sort_by: SortOrder) -> List[Dict]:
        """Sort memories by specified order"""
        if sort_by == SortOrder.NEWEST_FIRST:
            return sorted(memories, key=lambda m: m.get("timestamp", ""), reverse=True)
        elif sort_by == SortOrder.OLDEST_FIRST:
            return sorted(memories, key=lambda m: m.get("timestamp", ""))
        elif sort_by == SortOrder.HIGHEST_SCORE:
            return sorted(memories, key=lambda m: m.get("score", 0.0), reverse=True)
        elif sort_by == SortOrder.LOWEST_SCORE:
            return sorted(memories, key=lambda m: m.get("score", 0.0))
        return memories

    @staticmethod
    def _parse_timestamp(timestamp_str: str) -> datetime:
        """Parse ISO timestamp string"""
        try:
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except:
            return datetime.min

    @staticmethod
    def _score_to_relevance(score: float) -> str:
        """Convert score to relevance label"""
        if score >= 0.9:
            return "Very High"
        elif score >= 0.8:
            return "High"
        elif score >= 0.7:
            return "Medium"
        elif score >= 0.6:
            return "Low"
        else:
            return "Very Low"

    @staticmethod
    def _format_as_csv(export_data: Dict) -> str:
        """Format export data as CSV"""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Write memories
        writer.writerow(["Type", "ID", "Text", "Score", "Timestamp"])
        for memory in export_data.get("memories", []):
            writer.writerow(
                [
                    "Memory",
                    memory.get("id", ""),
                    memory.get("text", ""),
                    memory.get("score", 0.0),
                    memory.get("timestamp", ""),
                ]
            )

        # Write profile
        for key, value in export_data.get("profile", {}).items():
            writer.writerow(["Profile", key, str(value), "", ""])

        return output.getvalue()
