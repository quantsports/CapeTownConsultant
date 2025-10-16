"""
Google Custom Search implementation
"""

import asyncio
import aiolimiter
from tenacity import retry, stop_after_attempt, wait_exponential
import time

from src.services.search.base import BaseSearchEngine
from src.core.models import ToolResult
from src.config.settings import Config
from src.services.cost_tracker import CostTracker
from src.core.metrics import get_metrics


class GoogleSearch(BaseSearchEngine):
    """Google Custom Search API"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = Config.GOOGLE_SEARCH_API_KEY
        self.engine_id = Config.GOOGLE_SEARCH_ENGINE_ID
        self._rate_limiter = None
        self._rate_limiter_loop = None

    @property
    def rate_limiter(self):
        """Get or create rate limiter for current event loop - thread-safe"""
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create new limiter without loop reference
            if self._rate_limiter is None:
                self._rate_limiter = aiolimiter.AsyncLimiter(Config.SERPAPI_RPM, 60)
            self._rate_limiter_loop = None
            return self._rate_limiter

        # Check if we're in a different event loop
        if self._rate_limiter_loop is not current_loop:
            # Create new rate limiter for this event loop
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
        """Search using Google Custom Search"""
        metrics = get_metrics()
        metrics.record_tool_usage("google")
        _t0 = time.perf_counter()
        if not self.api_key or not self.engine_id:
            metrics.record_response_time("google", (time.perf_counter() - _t0) * 1000.0)
            return ToolResult(
                success=False,
                error="google failed: ConfigError - API key/engine not configured",
                source="google"
            )

        # Check budget
        if self.cost_tracker and not await self.cost_tracker.check_budget(
                user_id, "google-search"
        ):
            metrics.record_response_time("google", (time.perf_counter() - _t0) * 1000.0)
            return ToolResult(
                success=False,
                error="google failed: BudgetError - Daily budget limit exceeded",
                source="google"
            )

        async with self.rate_limiter:
            try:
                url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    "key": self.api_key,
                    "cx": self.engine_id,
                    "q": query,
                    "num": min(num_results, 10),  # Google API max is 10
                }

                response = await self.http_client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                results = []
                citations = []

                for item in data.get("items", [])[:num_results]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                    })
                    if item.get("link"):
                        citations.append(item["link"])

                # Record cost
                if self.cost_tracker:
                    await self.cost_tracker.record_cost(user_id, "google-search")

                metrics.record_response_time("google", (time.perf_counter() - _t0) * 1000.0)
                return ToolResult(
                    success=True,
                    data={"results": results, "query": query},
                    citations=citations,
                    source="google",
                    cost=CostTracker.COSTS["google-search"]
                )

            except Exception as e:
                metrics.record_response_time("google", (time.perf_counter() - _t0) * 1000.0)
                return ToolResult(
                    success=False,
                    error=f"google failed: {e.__class__.__name__} - {str(e)}",
                    source="google"
                )