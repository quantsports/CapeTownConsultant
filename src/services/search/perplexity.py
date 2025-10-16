"""
Perplexity AI search implementation
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


class PerplexitySearch(BaseSearchEngine):
    """Perplexity AI search for complex queries"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = Config.PERPLEXITY_API_KEY
        self._rate_limiter = None
        self._rate_limiter_loop = None

    @property
    def rate_limiter(self):
        """Get or create rate limiter for current event loop"""
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create new limiter
            self._rate_limiter = aiolimiter.AsyncLimiter(Config.PERPLEXITY_RPM, 60)
            self._rate_limiter_loop = None
            return self._rate_limiter
        
        # Check if we're in a different loop
        if self._rate_limiter_loop is not current_loop:
            self._rate_limiter = aiolimiter.AsyncLimiter(Config.PERPLEXITY_RPM, 60)
            self._rate_limiter_loop = current_loop
        
        return self._rate_limiter

    @retry(
        stop=stop_after_attempt(Config.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def search(self, query: str, user_id: str = "default") -> ToolResult:
        """Search using Perplexity AI"""
        metrics = get_metrics()
        metrics.record_tool_usage("perplexity")
        _t0 = time.perf_counter()
        if not self.api_key:
            metrics.record_response_time("perplexity", (time.perf_counter() - _t0) * 1000.0)
            return ToolResult(
                success=False,
                error="perplexity failed: ConfigError - API key not configured",
                source="perplexity"
            )

        # Check budget
        if self.cost_tracker and not await self.cost_tracker.check_budget(
                user_id, "perplexity"
        ):
            metrics.record_response_time("perplexity", (time.perf_counter() - _t0) * 1000.0)
            return ToolResult(
                success=False,
                error="Daily budget limit exceeded",
                source="perplexity"
            )

        async with self.rate_limiter:
            try:
                url = "https://api.perplexity.ai/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": "llama-3.1-sonar-large-128k-online",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Be precise and do a deep dive. Provide factual information."
                        },
                        {"role": "user", "content": query}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 2048,
                    "top_p": 0.9,
                    "return_citations": False,
                    "search_recency_filter": "month",
                    "stream": False
                }

                response = await self.http_client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

                answer = data["choices"][0]["message"]["content"]
                citations = data.get("citations", [])

                results = {
                    "answer": answer,
                    "query": query,
                    "model": data.get("model", ""),
                    "usage": data.get("usage", {})
                }

                # Record cost
                if self.cost_tracker:
                    await self.cost_tracker.record_cost(user_id, "perplexity")

                metrics.record_response_time("perplexity", (time.perf_counter() - _t0) * 1000.0)
                return ToolResult(
                    success=True,
                    data=results,
                    citations=citations,
                    source="perplexity",
                    cost=CostTracker.COSTS["perplexity"]
                )

            except Exception as e:
                metrics.record_response_time("perplexity", (time.perf_counter() - _t0) * 1000.0)
                return ToolResult(
                    success=False,
                    error=f"perplexity failed: {e.__class__.__name__} - {str(e)}",
                    source="perplexity"
                )