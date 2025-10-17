"""
Perplexity AI search implementation
Enhanced with proper error handling and logging
"""

import aiolimiter
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import asyncio
import time
from typing import Optional
import httpx

from src.services.search.base import BaseSearchEngine
from src.core.models import ToolResult
from src.config.settings import Config
from src.services.cost_tracker import CostTracker
from src.core.metrics import get_metrics
from src.core.logging import logger


class PerplexitySearch(BaseSearchEngine):
    """Perplexity AI search for complex queries with enhanced reliability"""

    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        super().__init__(cost_tracker=cost_tracker)
        self.api_key = Config.PERPLEXITY_API_KEY
        self._rate_limiter = None
        self._rate_limiter_loop = None
        self.http_client: Optional[httpx.AsyncClient] = None
        if self.api_key is None:
            raise ValueError("Perplexity API key not configured")

    @property
    def rate_limiter(self):
        """Get or create rate limiter for current event loop"""
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop - create limiter if needed
            if self._rate_limiter is None:
                self._rate_limiter = aiolimiter.AsyncLimiter(Config.PERPLEXITY_RPM, 60)
            return self._rate_limiter

        # Check if we need a new limiter for this loop
        if self._rate_limiter is None or self._rate_limiter_loop is not current_loop:
            self._rate_limiter = aiolimiter.AsyncLimiter(Config.PERPLEXITY_RPM, 60)
            self._rate_limiter_loop = current_loop

        return self._rate_limiter

    async def __aenter__(self):
        """Initialize HTTP client"""
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(Config.TIMEOUT_SECONDS),
            follow_redirects=True
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup HTTP client"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None

    def _validate_response(self, data: dict) -> tuple[bool, Optional[str]]:
        """Validate API response structure"""
        if not isinstance(data, dict):
            return False, "Response is not a dictionary"

        if "choices" not in data:
            return False, "Missing 'choices' field in response"

        if not data["choices"]:
            return False, "Empty 'choices' array"

        if "message" not in data["choices"][0]:
            return False, "Missing 'message' in first choice"

        if "content" not in data["choices"][0]["message"]:
            return False, "Missing 'content' in message"

        return True, None

    @retry(
        stop=stop_after_attempt(Config.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, asyncio.TimeoutError)),
        reraise=True
    )
    async def search(self, query: str, user_id: str = "default") -> ToolResult:
        """
        Search using Perplexity AI with comprehensive error handling

        Args:
            query: Search query
            user_id: User identifier for cost tracking

        Returns:
            ToolResult with answer and citations
        """
        metrics = get_metrics()
        metrics.record_tool_usage("perplexity")
        start_time = time.perf_counter()

        # Validate configuration
        if not self.api_key:
            logger.error("perplexity_not_configured", user_id=user_id)
            metrics.record_response_time("perplexity", (time.perf_counter() - start_time) * 1000.0)
            return ToolResult(
                success=False,
                error="Perplexity API key not configured",
                source="perplexity"
            )

        # Validate HTTP client
        if not self.http_client:
            logger.error("perplexity_client_not_initialized", user_id=user_id)
            metrics.record_response_time("perplexity", (time.perf_counter() - start_time) * 1000.0)
            return ToolResult(
                success=False,
                error="HTTP client not initialized. Use 'async with' context manager.",
                source="perplexity"
            )

        # Validate query
        if not query or not query.strip():
            logger.warning("perplexity_empty_query", user_id=user_id)
            metrics.record_response_time("perplexity", (time.perf_counter() - start_time) * 1000.0)
            return ToolResult(
                success=False,
                error="Query cannot be empty",
                source="perplexity"
            )

        # Check budget
        if self.cost_tracker:
            # Use proper cost type - check what's available in CostTracker.COSTS
            has_budget = await self.cost_tracker.check_budget(user_id, "perplexity-input", 100)
            if not has_budget:
                logger.warning("perplexity_budget_exceeded", user_id=user_id)
                metrics.record_response_time("perplexity", (time.perf_counter() - start_time) * 1000.0)
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
                    "max_tokens": 1024,
                    "top_p": 0.9,
                    "return_citations": True,  # ✅ Changed to True to get citations
                    "search_recency_filter": "month",
                    "stream": False
                }

                logger.info("perplexity_request", query=query[:100], user_id=user_id)

                response = await self.http_client.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=Config.TIMEOUT_SECONDS
                )

                # Check HTTP status
                if response.status_code != 200:
                    error_body = response.text
                    logger.error("perplexity_http_error",
                                status=response.status_code,
                                error=error_body[:500],
                                user_id=user_id)
                    metrics.record_response_time("perplexity", (time.perf_counter() - start_time) * 1000.0)
                    return ToolResult(
                        success=False,
                        error=f"HTTP {response.status_code}: {error_body[:200]}",
                        source="perplexity"
                    )

                response.raise_for_status()
                data = response.json()

                # Validate response structure
                is_valid, validation_error = self._validate_response(data)
                if not is_valid:
                    logger.error("perplexity_invalid_response",
                                error=validation_error,
                                response_keys=list(data.keys()) if isinstance(data, dict) else "not_dict",
                                user_id=user_id)
                    metrics.record_response_time("perplexity", (time.perf_counter() - start_time) * 1000.0)
                    return ToolResult(
                        success=False,
                        error=f"Invalid API response: {validation_error}",
                        source="perplexity"
                    )

                # Extract data
                answer = data["choices"][0]["message"]["content"]
                citations = data.get("citations", [])
                usage = data.get("usage", {})
                model = data.get("model", "llama-3.1-sonar-large-128k-online")

                results = {
                    "answer": answer,
                    "query": query,
                    "model": model,
                    "usage": usage,
                    "citations_count": len(citations)
                }

                # Record cost if tracker available
                if self.cost_tracker and usage:
                    # Record based on token usage if available
                    input_tokens = usage.get("prompt_tokens", 0)
                    output_tokens = usage.get("completion_tokens", 0)

                    if input_tokens > 0:
                        await self.cost_tracker.record_cost(user_id, "perplexity-input", input_tokens)
                    if output_tokens > 0:
                        await self.cost_tracker.record_cost(user_id, "perplexity-output", output_tokens)

                duration_ms = (time.perf_counter() - start_time) * 1000.0
                metrics.record_response_time("perplexity", duration_ms)

                logger.info("perplexity_success",
                           answer_length=len(answer),
                           citations=len(citations),
                           duration_ms=int(duration_ms),
                           user_id=user_id)

                return ToolResult(
                    success=True,
                    data=results,
                    citations=citations,
                    source="perplexity",
                    cost=CostTracker.COSTS.get("perplexity", 0.0)
                )

            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                logger.error("perplexity_http_status_error",
                            status=e.response.status_code,
                            error=str(e)[:500],
                            user_id=user_id)
                metrics.record_response_time("perplexity", (time.perf_counter() - start_time) * 1000.0)
                return ToolResult(
                    success=False,
                    error=f"Perplexity API error: {error_msg}",
                    source="perplexity"
                )

            except httpx.TimeoutException as e:
                logger.error("perplexity_timeout",
                            error=str(e),
                            timeout=Config.TIMEOUT_SECONDS,
                            user_id=user_id)
                metrics.record_response_time("perplexity", (time.perf_counter() - start_time) * 1000.0)
                return ToolResult(
                    success=False,
                    error=f"Request timed out after {Config.TIMEOUT_SECONDS}s",
                    source="perplexity"
                )

            except httpx.RequestError as e:
                logger.error("perplexity_request_error",
                            error=str(e),
                            error_type=type(e).__name__,
                            user_id=user_id)
                metrics.record_response_time("perplexity", (time.perf_counter() - start_time) * 1000.0)
                return ToolResult(
                    success=False,
                    error=f"Request failed: {str(e)}",
                    source="perplexity"
                )

            except ValueError as e:
                # JSON decode error
                logger.error("perplexity_json_error",
                            error=str(e),
                            user_id=user_id)
                metrics.record_response_time("perplexity", (time.perf_counter() - start_time) * 1000.0)
                return ToolResult(
                    success=False,
                    error=f"Invalid JSON response: {str(e)}",
                    source="perplexity"
                )

            except Exception as e:
                logger.error("perplexity_unexpected_error",
                            error=str(e),
                            error_type=type(e).__name__,
                            user_id=user_id)
                metrics.record_response_time("perplexity", (time.perf_counter() - start_time) * 1000.0)
                return ToolResult(
                    success=False,
                    error=f"Unexpected error: {type(e).__name__} - {str(e)}",
                    source="perplexity"
                )