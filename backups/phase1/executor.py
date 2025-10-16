"""
Tool executor
Validates and executes tool calls
"""

from typing import Dict, Optional, Tuple

from src.core.models import ToolResult, ToolType
from src.core.logging import logger
from src.services.cost_tracker import CostTracker
from src.services.embeddings import EmbeddingService
from src.services.search import (
    WikipediaSearch,
    SerpAPISearch,
    GoogleSearch,
    PerplexitySearch
)
from src.memory import VectorMemory, ProfileManager, UnifiedMemorySystem
from src.tools.schemas import ToolSchemas


class ToolExecutor:
    """Enhanced tool executor with validation"""

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

    async def __aenter__(self):
        """Initialize search engines"""
        self.wiki_search = await WikipediaSearch(self.cost_tracker).__aenter__()
        self.serpapi_search = await SerpAPISearch(self.cost_tracker).__aenter__()
        self.google_search = await GoogleSearch(self.cost_tracker).__aenter__()
        self.perplexity_search = await PerplexitySearch(self.cost_tracker).__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup search engines"""
        for engine in [
            self.wiki_search,
            self.serpapi_search,
            self.google_search,
            self.perplexity_search
        ]:
            if engine:
                await engine.__aexit__(exc_type, exc_val, exc_tb)

    def validate_tool_call(
            self,
            tool_name: str,
            arguments: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Enhanced validation with schemas"""
        try:
            if tool_name not in ToolSchemas.SCHEMAS:
                return False, f"Unknown tool: {tool_name}"

            schema = ToolSchemas.SCHEMAS[tool_name]

            # Check required parameters
            for param in schema["required"]:
                if param not in arguments:
                    return False, f"Missing required parameter: {param}"

                # Type validation for specific parameters
                if param == "items" and not isinstance(arguments[param], list):
                    return False, f"Parameter 'items' must be a list"
                if param == "keys" and not isinstance(arguments[param], list):
                    return False, f"Parameter 'keys' must be a list"
                if param == "data" and not isinstance(arguments[param], dict):
                    return False, f"Parameter 'data' must be a dict"

            # Check optional parameters
            for param, expected_type in schema["optional"].items():
                if param in arguments and not isinstance(arguments[param], expected_type):
                    return False, f"Parameter '{param}' must be of type {expected_type.__name__}"

            # Deep validation for items parameter
            if "items" in arguments:
                if not isinstance(arguments["items"], list):
                    return False, f"Parameter 'items' must be a list"
                # Validate each item has required 'text' field
                for i, item in enumerate(arguments["items"]):
                    if not isinstance(item, dict):
                        return False, f"Item {i} must be a dictionary"
                    if "text" not in item:
                        return False, f"Item {i} missing required 'text' field"

            return True, None

        except Exception as e:
            return False, str(e)

    async def execute(
            self,
            tool_name: str,
            arguments: Dict,
            user_id: str = "default"
    ) -> ToolResult:
        """Execute a tool with validation"""
        # Validate tool call
        is_valid, error = self.validate_tool_call(tool_name, arguments)
        if not is_valid:
            return ToolResult(success=False, error=error)

        try:
            # Execute appropriate tool
            if tool_name == ToolType.WEB_SEARCH.value:
                return await self.serpapi_search.search(
                    arguments.get("query", ""),
                    user_id,
                    arguments.get("num", 5)
                )

            elif tool_name == ToolType.PERPLEXITY_SEARCH.value:
                return await self.perplexity_search.search(
                    arguments.get("query", ""),
                    user_id
                )

            elif tool_name == ToolType.GOOGLE_SEARCH.value:
                return await self.google_search.search(
                    arguments.get("query", ""),
                    user_id,
                    arguments.get("num", 5)
                )

            elif tool_name == ToolType.WIKI_FETCH.value:
                return await self.wiki_search.search(
                    arguments.get("query", ""),
                    user_id,
                    arguments.get("limit", 3)
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
                return await self.vector_memory.upsert(
                    arguments.get("items", []),
                    namespace,
                    user_id
                )

            elif tool_name == ToolType.PROFILE_READ.value:
                data = await self.profile_manager.read(
                    user_id,
                    arguments.get("keys")
                )
                return ToolResult(success=True, data=data)

            elif tool_name == ToolType.PROFILE_WRITE.value:
                success = await self.profile_manager.write(
                    user_id,
                    arguments.get("data", {})
                )
                return ToolResult(
                    success=success,
                    data={"updated": list(arguments.get("data", {}).keys())}
                )

            else:
                return ToolResult(
                    success=False,
                    error=f"Tool not implemented: {tool_name}"
                )

        except Exception as e:
            logger.error("tool_execution_failed", tool=tool_name, error=str(e))
            return ToolResult(
                success=False,
                error=f"Tool execution failed: {str(e)}"
            )