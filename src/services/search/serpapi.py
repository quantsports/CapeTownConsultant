"""
SerpAPI search implementation
"""

import aiolimiter
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncio
import time
from src.services.search.base import BaseSearchEngine
from src.core.models import ToolResult
from src.config.settings import Config
from src.services.cost_tracker import CostTracker
from src.core.metrics import get_metrics


class SerpAPISearch(BaseSearchEngine):
    """SerpAPI web search"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = Config.SERPAPI_API_KEY
        self._rate_limiter = None
        self._rate_limiter_loop = None

    @property
    def rate_limiter(self):
        """Get or create rate limiter for current event loop"""
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create new limiter
            self._rate_limiter = aiolimiter.AsyncLimiter(Config.SERPAPI_RPM, 60)
            self._rate_limiter_loop = None
            return self._rate_limiter
        
        # Check if we're in a different loop
        if self._rate_limiter_loop is not current_loop:
            self._rate_limiter = aiolimiter.AsyncLimiter(Config.SERPAPI_RPM, 60)
            self._rate_limiter_loop = current_loop
        
        return self._rate_limiter

    @retry(
        stop=stop_after_attempt(Config.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def search(
            self,
            query: str,
            user_id: str = "default",
            num_results: int = 5
    ) -> ToolResult:
        """Search using SerpAPI"""
        metrics = get_metrics()
        metrics.record_tool_usage("serpapi")
        _t0 = time.perf_counter()
        if not self.api_key:
            metrics.record_response_time("serpapi", (time.perf_counter() - _t0) * 1000.0)
            return ToolResult(
                success=False,
                error="serpapi failed: ConfigError - API key not configured",
                source="serpapi"
            )

        # Check budget
        if self.cost_tracker and not await self.cost_tracker.check_budget(user_id, "serpapi"):
            metrics.record_response_time("serpapi", (time.perf_counter() - _t0) * 1000.0)
            return ToolResult(
                success=False,
                error="serpapi failed: BudgetError - Daily budget limit exceeded",
                source="serpapi"
            )

        async with self.rate_limiter:
            try:
                url = "https://serpapi.com/search"
                params = {
                    "q": query,
                    "api_key": self.api_key,
                    "num": num_results,
                    "engine": "google"
                }

                response = await self.http_client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                results = []
                citations = []

                # Parse organic results
                for result in data.get("organic_results", [])[:num_results]:
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("link", ""),
                        "snippet": result.get("snippet", ""),
                        "position": result.get("position", 0)
                    })
                    if result.get("link"):
                        citations.append(result["link"])

                # Parse knowledge graph if present
                if "knowledge_graph" in data:
                    kg = data["knowledge_graph"]
                    kg_url = kg.get("source", {}).get("link", "")
                    results.insert(0, {
                        "title": kg.get("title", ""),
                        "url": kg_url,
                        "snippet": kg.get("description", ""),
                        "type": "knowledge_graph"
                    })
                    if kg_url:
                        citations.insert(0, kg_url)

                # Record cost
                if self.cost_tracker:
                    await self.cost_tracker.record_cost(user_id, "serpapi")

                metrics.record_response_time("serpapi", (time.perf_counter() - _t0) * 1000.0)
                return ToolResult(
                    success=True,
                    data={"results": results, "query": query},
                    citations=citations,
                    source="serpapi",
                    cost=CostTracker.COSTS["serpapi"]
                )

            except Exception as e:
                metrics.record_response_time("serpapi", (time.perf_counter() - _t0) * 1000.0)
                return ToolResult(
                    success=False,
                    error=f"serpapi failed: {e.__class__.__name__} - {str(e)}",
                    source="serpapi"
                )