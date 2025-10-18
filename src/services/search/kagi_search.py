"""
Kagi FastGPT search integration
AI-powered search with LLM synthesis backed by a real search engine
"""

import asyncio
import time
from typing import Optional
import aiolimiter
from tenacity import retry, stop_after_attempt, wait_exponential

from src.services.search.base import BaseSearchEngine
from src.core.models import ToolResult
from src.core.logging import logger
from src.config.settings import Config
from src.services.cost_tracker import CostTracker


class KagiSearch(BaseSearchEngine):
    """
    Kagi FastGPT search engine

    Uses Kagi's FastGPT API which combines LLM reasoning with web search.
    Think ChatGPT but with live search engine backing for accuracy.

    Pricing: $0.015 per query (1.5¢)
    Documentation: https://help.kagi.com/kagi/api/fastgpt.html
    """

    def __init__(
        self, api_key: Optional[str] = None, cost_tracker: Optional[CostTracker] = None
    ):
        """
        Initialize Kagi search

        Args:
            api_key: Kagi API token (from settings if not provided)
            cost_tracker: Optional cost tracker for budget management
        """
        super().__init__(cost_tracker=cost_tracker)
        self.api_key = api_key or getattr(Config, "KAGI_API_KEY", None)
        self._rate_limiter = None
        self._rate_limiter_loop = None

    @property
    def rate_limiter(self):
        """
        Get or create rate limiter for current event loop
        Thread-safe implementation that handles event loop changes
        """
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create new limiter without loop reference
            if self._rate_limiter is None:
                # Conservative rate limit: 30 requests per minute
                self._rate_limiter = aiolimiter.AsyncLimiter(30, 60)
            self._rate_limiter_loop = None
            return self._rate_limiter

        # Check if we're in a different event loop
        if self._rate_limiter_loop is not current_loop:
            # Create new rate limiter for this event loop
            self._rate_limiter = aiolimiter.AsyncLimiter(30, 60)
            self._rate_limiter_loop = current_loop

        return self._rate_limiter

    def is_configured(self) -> bool:
        """Check if Kagi API key is configured"""
        return self.api_key is not None and self.api_key != ""

    @retry(
        stop=stop_after_attempt(Config.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def search(
        self, query: str, user_id: str = "default", allow_cache: bool = True
    ) -> ToolResult:
        """
        Search using Kagi FastGPT

        Args:
            query: Search query to be answered
            user_id: User identifier for cost tracking
            allow_cache: Whether to allow cached responses (default: True)

        Returns:
            ToolResult with answer, citations, and metadata
        """
        start_time = time.perf_counter()

        # Check configuration
        if not self.is_configured():
            logger.warning("kagi_not_configured", user_id=user_id)
            return ToolResult(
                success=False,
                error="Kagi API key not configured. Set KAGI_API_KEY in .env",
                source="kagi",
            )

        # Validate query
        if not query or not query.strip():
            logger.warning("kagi_empty_query", user_id=user_id)
            return ToolResult(
                success=False, error="Query cannot be empty", source="kagi"
            )

        # Check budget (Kagi is $0.015 per query)
        if self.cost_tracker:
            has_budget = await self.cost_tracker.check_budget(
                user_id, "kagi-search", 1  # Flat rate per query
            )
            if not has_budget:
                logger.warning("kagi_budget_exceeded", user_id=user_id)
                return ToolResult(
                    success=False, error="Daily budget limit exceeded", source="kagi"
                )

        async with self.rate_limiter:
            try:
                url = "https://kagi.com/api/v0/fastgpt"
                headers = {
                    "Authorization": f"Bot {self.api_key}",
                    "Content-Type": "application/json",
                }

                payload = {
                    "query": query,
                    "cache": allow_cache,
                    "web_search": True,  # Currently required, cannot be False
                }

                logger.debug(
                    "kagi_request",
                    query_length=len(query),
                    user_id=user_id,
                    cache_enabled=allow_cache,
                )

                response = await self.http_client.post(
                    url, json=payload, headers=headers
                )
                response.raise_for_status()
                data = response.json()

                # Extract response data
                meta = data.get("meta", {})
                result_data = data.get("data", {})

                output = result_data.get("output", "")
                references = result_data.get("references", [])
                tokens = result_data.get("tokens", 0)

                # Extract citations from references
                citations = [ref.get("url") for ref in references if ref.get("url")]

                # Format results
                results = {
                    "answer": output,
                    "query": query,
                    "tokens": tokens,
                    "node": meta.get("node", "unknown"),
                    "request_id": meta.get("id", ""),
                    "processing_ms": meta.get("ms", 0),
                    "references": [
                        {
                            "title": ref.get("title", ""),
                            "snippet": ref.get("snippet", ""),
                            "url": ref.get("url", ""),
                        }
                        for ref in references
                    ],
                }

                # Record cost
                if self.cost_tracker:
                    await self.cost_tracker.record_cost(
                        user_id, "kagi-search", 1  # Flat rate per query
                    )

                elapsed = (time.perf_counter() - start_time) * 1000
                logger.info(
                    "kagi_search_success",
                    user_id=user_id,
                    duration_ms=elapsed,
                    tokens=tokens,
                    references_count=len(references),
                    cached=meta.get("cached", False),
                )

                return ToolResult(
                    success=True,
                    data=results,
                    citations=citations,
                    source="kagi",
                    cost=0.015,  # $0.015 per query
                )

            except Exception as e:
                error_msg = str(e)

                # Check for specific error types
                if "Insufficient credit" in error_msg:
                    logger.error(
                        "kagi_insufficient_credits", user_id=user_id, error=error_msg
                    )
                    return ToolResult(
                        success=False,
                        error="Kagi API credits exhausted. Please top up at https://kagi.com/settings?p=billing_api",
                        source="kagi",
                    )

                if hasattr(e, "response") and hasattr(e.response, "status_code"):
                    status_code = e.response.status_code
                    logger.error(
                        "kagi_http_error",
                        user_id=user_id,
                        status=status_code,
                        error=error_msg,
                    )

                    if status_code == 401:
                        return ToolResult(
                            success=False,
                            error="Kagi API authentication failed. Check your API key.",
                            source="kagi",
                        )
                    elif status_code == 429:
                        return ToolResult(
                            success=False,
                            error="Kagi API rate limit exceeded. Please wait before retrying.",
                            source="kagi",
                        )

                logger.error("kagi_search_failed", user_id=user_id, error=error_msg)

                return ToolResult(
                    success=False,
                    error=f"Kagi search failed: {error_msg}",
                    source="kagi",
                )
