"""
Perplexity AI search integration
FIXES: Critical #2 - Budget enforcement failure (wrong cost key)
FIXES: High #6 - Inaccurate budget estimation (proper token counting)
"""

import time
from typing import Optional
import httpx
import aiolimiter
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import Config
from src.core.models import ToolResult
from src.core.logging import logger
from src.services.cost_tracker import CostTracker


class PerplexitySearch:
    """Perplexity AI search engine with proper cost tracking"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        cost_tracker: Optional[CostTracker] = None,
        http_client: Optional[httpx.AsyncClient] = None
    ):
        self.api_key = api_key or Config.PERPLEXITY_API_KEY
        self.cost_tracker = cost_tracker

        # Use provided client or create new one
        self._http_client = http_client
        self._owns_client = http_client is None

        # Rate limiter
        self._rate_limiter = aiolimiter.AsyncLimiter(
            Config.PERPLEXITY_RPM, 60
        )

    async def __aenter__(self):
        """Async context manager entry"""
        if self._owns_client:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                limits=httpx.Limits(max_keepalive_connections=5)
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._owns_client and self._http_client:
            await self._http_client.aclose()

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get HTTP client"""
        if self._http_client is None:
            raise RuntimeError("PerplexitySearch must be used as async context manager")
        return self._http_client

    @property
    def rate_limiter(self) -> aiolimiter.AsyncLimiter:
        """Get rate limiter"""
        return self._rate_limiter

    def is_configured(self) -> bool:
        """Check if API key is configured"""
        return self.api_key is not None and self.api_key != ""

    @retry(
        stop=stop_after_attempt(Config.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def search(
        self,
        query: str,
        user_id: str = "default"
    ) -> ToolResult:
        """
        Search using Perplexity AI

        CRITICAL FIX #2: Use correct cost key "perplexity" not "perplexity-input"
        HIGH FIX #6: Estimate tokens from query length instead of arbitrary 100
        """
        start_time = time.perf_counter()

        # Check configuration
        if not self.is_configured():
            logger.warning("perplexity_not_configured", user_id=user_id)
            return ToolResult(
                success=False,
                error="Perplexity API key not configured",
                source="perplexity"
            )

        # Check if client is available
        if self._http_client is None:
            return ToolResult(
                success=False,
                error="PerplexitySearch not initialized. Use 'async with' context manager.",
                source="perplexity"
            )

        # Validate query
        if not query or not query.strip():
            logger.warning("perplexity_empty_query", user_id=user_id)
            return ToolResult(
                success=False,
                error="Query cannot be empty",
                source="perplexity"
            )

        # HIGH FIX #6: Estimate tokens from query length instead of arbitrary 100
        # Rough estimate: ~4 characters per token (including system prompt overhead)
        estimated_input_tokens = (len(query) + 200) // 4  # 200 chars for system prompt

        # CRITICAL FIX #2: Use correct cost key "perplexity" instead of "perplexity-input"
        if self.cost_tracker:
            # Check budget with estimated tokens
            has_budget = await self.cost_tracker.check_budget(
                user_id,
                "perplexity",  # FIXED: Was "perplexity-input"
                estimated_input_tokens
            )
            if not has_budget:
                logger.warning("perplexity_budget_exceeded", user_id=user_id)
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
                    "model": "sonar",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Be precise and do a deep dive. Provide factual information with sources."
                        },
                        {"role": "user", "content": query}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 2048,
                    "top_p": 0.9,
                    "return_citations": True,
                    "search_recency_filter": "month",
                    "stream": False
                }

                response = await self.http_client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

                answer = data["choices"][0]["message"]["content"]
                citations = data.get("citations", [])
                usage = data.get("usage", {})

                results = {
                    "answer": answer,
                    "query": query,
                    "model": data.get("model", "sonar"),
                    "usage": usage
                }

                # Record actual cost based on usage if available
                if self.cost_tracker:
                    actual_tokens = usage.get("total_tokens", estimated_input_tokens)
                    await self.cost_tracker.record_cost(
                        user_id,
                        "perplexity",  # FIXED: Consistent cost key
                        actual_tokens
                    )

                elapsed = (time.perf_counter() - start_time) * 1000
                logger.info(
                    "perplexity_search_success",
                    user_id=user_id,
                    duration_ms=elapsed,
                    tokens=usage.get("total_tokens", "unknown")
                )

                return ToolResult(
                    success=True,
                    data=results,
                    citations=citations,
                    source="perplexity",
                    cost=CostTracker.COSTS.get("perplexity", 0.0) * usage.get("total_tokens", estimated_input_tokens)
                )

            except httpx.HTTPStatusError as e:
                logger.error(
                    "perplexity_http_error",
                    user_id=user_id,
                    status=e.response.status_code,
                    error=str(e)
                )
                return ToolResult(
                    success=False,
                    error=f"Perplexity API error: {e.response.status_code}",
                    source="perplexity"
                )
            except Exception as e:
                logger.error(
                    "perplexity_search_failed",
                    user_id=user_id,
                    error=str(e)
                )
                return ToolResult(
                    success=False,
                    error=f"Perplexity search failed: {str(e)}",
                    source="perplexity"
                )