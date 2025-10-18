"""
Tool executor
Validates and executes tool calls with metrics collection
"""

import time
from typing import Dict, Optional, Tuple

from src.core.models import ToolResult, ToolType
from src.core.logging import logger
from src.services.cost_tracker import CostTracker
from src.services.embeddings import EmbeddingService
from src.services.search import (
    WikipediaSearch,
    SerpAPISearch,
    GoogleSearch,
    PerplexitySearch,
    KagiSearch
)
from src.memory import VectorMemory, ProfileManager, UnifiedMemorySystem
from src.tools.schemas import ToolSchemas


class ToolExecutor:
    """Enhanced tool executor with validation and metrics"""

    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        self.cost_tracker = cost_tracker
        self.embedding_service = EmbeddingService(cost_tracker=cost_tracker)
        self.vector_memory = VectorMemory(self.embedding_service)
        self.profile_manager = ProfileManager()
        self.unified_memory = UnifiedMemorySystem(
            self.vector_memory,
            self.profile_manager
        )

        # Search engines (initialized on enter)
        self.wiki_search: Optional[WikipediaSearch] = None
        self.serpapi_search: Optional[SerpAPISearch] = None
        self.google_search: Optional[GoogleSearch] = None
        self.perplexity_search: Optional[PerplexitySearch] = None
        self.kagi_search: Optional[KagiSearch] = None

        # Metrics tracking
        self.execution_metrics: Dict[str, Dict] = {}

    async def __aenter__(self):
        """Initialize search engines with proper error handling"""
        try:
            self.wiki_search = await WikipediaSearch(self.cost_tracker).__aenter__()
            self.serpapi_search = await SerpAPISearch(self.cost_tracker).__aenter__()
            self.google_search = await GoogleSearch(self.cost_tracker).__aenter__()
            self.perplexity_search = await PerplexitySearch(self.cost_tracker).__aenter__()
            self.kagi_search = await KagiSearch(self.cost_tracker).__aenter__()
            return self
        except Exception as e:
            # Cleanup partially initialized engines
            await self.__aexit__(None, None, None)
            raise RuntimeError(f"Failed to initialize ToolExecutor: {e}") from e

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup all search engines, even if some fail"""
        engines = [
            self.wiki_search,
            self.serpapi_search,
            self.google_search,
            self.perplexity_search,
            self.kagi_search
        ]

        errors = []
        for engine in engines:
            if engine:
                try:
                    await engine.__aexit__(exc_type, exc_val, exc_tb)
                except Exception as e:
                    errors.append(f"{engine.__class__.__name__}: {e}")

        if errors:
            logger.warning("cleanup_errors", errors=errors)

        # Reset all engines
        self.wiki_search = None
        self.serpapi_search = None
        self.google_search = None
        self.perplexity_search = None
        self.kagi_search = None

    @property
    def is_initialized(self) -> bool:
        """Check if all search engines are ready"""
        return all([
            self.wiki_search is not None,
            self.serpapi_search is not None,
            self.google_search is not None,
            self.perplexity_search is not None,
            self.kagi_search is not None
        ])

    def _sanitize_query(self, query: str, max_length: int = 500) -> str:
        """Sanitize search queries"""
        return query.strip()[:max_length]

    def validate_tool_call(
            self,
            tool_name: str,
            arguments: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Enhanced validation with schemas and deep item validation"""
        try:
            if tool_name not in ToolSchemas.SCHEMAS:
                return False, f"Unknown tool: {tool_name}"

            schema = ToolSchemas.SCHEMAS[tool_name]

            # Check required parameters
            for param in schema["required"]:
                if param not in arguments:
                    return False, f"Missing required parameter: {param}"

                # Validate non-empty strings
                if isinstance(arguments[param], str) and not arguments[param].strip():
                    return False, f"Parameter '{param}' cannot be empty"

                # ✅ ENHANCED: Deep validation for memory_upsert items
                if param == "items" and tool_name == "memory_upsert":
                    if not isinstance(arguments[param], list):
                        return False, f"Parameter 'items' must be a list"

                    if len(arguments[param]) == 0:
                        return False, f"Parameter 'items' cannot be empty"

                    # Validate each item structure
                    for i, item in enumerate(arguments[param]):
                        if not isinstance(item, dict):
                            return False, f"Item {i} must be a dictionary"
                        if "text" not in item:
                            return False, f"Item {i} missing required 'text' field"
                        if not isinstance(item["text"], str):
                            return False, f"Item {i} 'text' field must be a string"
                        if item["text"].strip() == "":
                            return False, f"Item {i} 'text' field cannot be empty"
                        # Validate optional 'meta' field
                        if "meta" in item and not isinstance(item["meta"], dict):
                            return False, f"Item {i} 'meta' field must be a dictionary"

                # Type validation for other list parameters
                elif param == "keys" and not isinstance(arguments[param], list):
                    return False, f"Parameter 'keys' must be a list"

                # Type validation for dict parameters
                elif param == "data" and not isinstance(arguments[param], dict):
                    return False, f"Parameter 'data' must be a dict"

                # Type validation for query parameters
                elif param == "query" and not isinstance(arguments[param], str):
                    return False, f"Parameter 'query' must be a string"

            # Check optional parameters
            for param, expected_type in schema["optional"].items():
                if param in arguments:
                    if not isinstance(arguments[param], expected_type):
                        return False, f"Parameter '{param}' must be of type {expected_type.__name__}"

                    # Validate numeric ranges
                    if param == "num":
                        if arguments[param] < 1 or arguments[param] > 100:
                            return False, "Parameter 'num' must be between 1 and 100"
                    elif param == "top_k":
                        if arguments[param] < 1 or arguments[param] > 50:
                            return False, "Parameter 'top_k' must be between 1 and 50"
                    elif param == "limit":
                        if arguments[param] < 1 or arguments[param] > 20:
                            return False, "Parameter 'limit' must be between 1 and 20"

            return True, None

        except Exception as e:
            logger.error("validation_error", tool=tool_name, error=str(e))
            return False, f"Validation error: {str(e)}"

    def _record_execution_metrics(
            self,
            tool_name: str,
            success: bool,
            execution_time: float,
            user_id: str,
            error: Optional[str] = None
    ):
        """Record execution metrics for analytics"""
        if tool_name not in self.execution_metrics:
            self.execution_metrics[tool_name] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "last_error": None
            }

        metrics = self.execution_metrics[tool_name]
        metrics["total_calls"] += 1

        if success:
            metrics["successful_calls"] += 1
        else:
            metrics["failed_calls"] += 1
            metrics["last_error"] = error

        metrics["total_time"] += execution_time
        metrics["avg_time"] = metrics["total_time"] / metrics["total_calls"]

    def get_metrics(self, tool_name: Optional[str] = None) -> Dict:
        """Get execution metrics for specific tool or all tools"""
        if tool_name:
            return self.execution_metrics.get(tool_name, {})
        return self.execution_metrics.copy()

    def reset_metrics(self):
        """Reset all execution metrics"""
        self.execution_metrics.clear()

    async def execute(
            self,
            tool_name: str,
            arguments: Dict,
            user_id: str = "default"
    ) -> ToolResult:
        """Execute a tool with validation and metrics"""
        start_time = time.time()

        # Validate initialization for search tools
        search_tools = {
            ToolType.WEB_SEARCH.value: self.serpapi_search,
            ToolType.PERPLEXITY_SEARCH.value: self.perplexity_search,
            ToolType.GOOGLE_SEARCH.value: self.google_search,
            ToolType.KAGI_SEARCH.value: self.kagi_search,
            ToolType.WIKI_FETCH.value: self.wiki_search,
        }

        if tool_name in search_tools and search_tools[tool_name] is None:
            error = "ToolExecutor not initialized. Use 'async with' context manager."
            self._record_execution_metrics(tool_name, False, time.time() - start_time, user_id, error)
            return ToolResult(success=False, error=error)

        # Validate tool call
        is_valid, error = self.validate_tool_call(tool_name, arguments)
        if not is_valid:
            logger.warning("tool_validation_failed", tool=tool_name, error=error)
            self._record_execution_metrics(tool_name, False, time.time() - start_time, user_id, error)
            return ToolResult(success=False, error=f"Validation failed: {error}")

        try:
            result = await self._execute_tool(tool_name, arguments, user_id)

            # Record metrics
            execution_time = time.time() - start_time
            self._record_execution_metrics(
                tool_name,
                result.success,
                execution_time,
                user_id,
                result.error
            )

            # Log execution metrics
            logger.info("tool_executed",
                       tool=tool_name,
                       success=result.success,
                       duration_ms=int(execution_time * 1000),
                       user_id=user_id)

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Tool execution failed: {str(e)}"

            self._record_execution_metrics(tool_name, False, execution_time, user_id, error_msg)
            logger.error("tool_execution_failed",
                        tool=tool_name,
                        error=str(e),
                        user_id=user_id,
                        duration_ms=int(execution_time * 1000))

            return ToolResult(success=False, error=error_msg)

    async def _execute_tool(
            self,
            tool_name: str,
            arguments: Dict,
            user_id: str
    ) -> ToolResult:
        """Internal method to execute specific tools"""

        if tool_name == ToolType.WEB_SEARCH.value:
            return await self.serpapi_search.search(
                self._sanitize_query(arguments.get("query", "")),
                user_id,
                arguments.get("num", 5)
            )

        elif tool_name == ToolType.PERPLEXITY_SEARCH.value:
            return await self.perplexity_search.search(
                self._sanitize_query(arguments.get("query", "")),
                user_id
            )

        elif tool_name == ToolType.GOOGLE_SEARCH.value:
            return await self.google_search.search(
                self._sanitize_query(arguments.get("query", "")),
                user_id,
                arguments.get("num", 5)
            )

        elif tool_name == ToolType.WIKI_FETCH.value:
            return await self.wiki_search.search(
                self._sanitize_query(arguments.get("query", "")),
                user_id,
                arguments.get("limit", 3)
            )

        elif tool_name == ToolType.KAGI_SEARCH.value:
            # Kagi FastGPT supports allow_cache flag
            return await self.kagi_search.search(
                self._sanitize_query(arguments.get("query", "")),
                user_id,
                arguments.get("allow_cache", True)
            )

        elif tool_name == ToolType.MEMORY_QUERY.value:
            namespace = f"user:{user_id}"
            return await self.vector_memory.query(
                arguments.get("text", ""),
                namespace,
                arguments.get("top_k", 5),
                arguments.get("filter"),
                user_id
            )

        elif tool_name == ToolType.MEMORY_UPSERT.value:
            namespace = f"user:{user_id}"
            items = arguments.get("items", [])
            if not items:
                return ToolResult(success=False, error="No items provided for memory upsert")
            return await self.vector_memory.upsert(items, namespace, user_id)

        elif tool_name == ToolType.PROFILE_READ.value:
            keys = arguments.get("keys")  # Can be None for full profile
            data = await self.profile_manager.read(user_id, keys)
            return ToolResult(
                success=True,
                data=data,
                source="profile_manager"
            )

        elif tool_name == ToolType.PROFILE_WRITE.value:
            data = arguments.get("data", {})
            if not data:
                return ToolResult(success=False, error="No data provided for profile write")

            success = await self.profile_manager.write(user_id, data)
            if not success:
                return ToolResult(success=False, error="Profile write operation failed")

            return ToolResult(
                success=True,
                data={"updated": list(data.keys())},
                source="profile_manager"
            )

        else:
            return ToolResult(
                success=False,
                error=f"Tool not implemented: {tool_name}"
            )