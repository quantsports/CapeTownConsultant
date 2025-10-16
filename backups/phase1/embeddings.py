"""
Embedding service
Generate and cache embeddings using OpenAI
"""

from typing import List, Optional
import asyncio
import aiolimiter
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import Config
from src.core.cache import PersistentEmbeddingCache
from src.services.cost_tracker import CostTracker


class EmbeddingService:
    """Generate and cache embeddings"""

    def __init__(self, api_key: Optional[str] = None, cost_tracker: Optional[CostTracker] = None):
        self.api_key = api_key or Config.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
        self.cache = PersistentEmbeddingCache()
        self.cost_tracker = cost_tracker
        self._rate_limiter = None
        self._rate_limiter_loop = None

    @property
    def rate_limiter(self):
        """Get or create rate limiter for current event loop"""
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            self._rate_limiter = aiolimiter.AsyncLimiter(Config.OPENAI_RPM, 60)
            self._rate_limiter_loop = None
            return self._rate_limiter
        
        if not hasattr(self, '_rate_limiter_loop') or self._rate_limiter_loop is not current_loop:
            self._rate_limiter = aiolimiter.AsyncLimiter(Config.OPENAI_RPM, 60)
            self._rate_limiter_loop = current_loop
        
        return self._rate_limiter

    @retry(
        stop=stop_after_attempt(Config.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def embed(self, text: str, user_id: str = "default") -> List[float]:
        """Generate embedding for text"""
        if not self.client:
            raise ValueError("OpenAI API key not configured")

        # Check cache first
        cached = await self.cache.get(text)
        if cached is not None:
            return cached

        # Check budget
        if self.cost_tracker and not await self.cost_tracker.check_budget(
                user_id, "embedding", len(text)
        ):
            raise ValueError("Daily budget limit exceeded")

        # Generate embedding
        async with self.rate_limiter:
            try:
                response = await self.client.embeddings.create(
                    model=Config.EMBEDDING_MODEL,
                    input=text[:8000]  # Truncate to max length
                )
                embedding = response.data[0].embedding

                # Cache result
                await self.cache.set(text, embedding)

                # Record cost
                if self.cost_tracker:
                    await self.cost_tracker.record_cost(user_id, "embedding", len(text))

                return embedding

            except Exception as e:
                raise Exception(f"Embedding generation failed: {str(e)}")

    async def embed_batch(
            self,
            texts: List[str],
            user_id: str = "default"
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if not self.client:
            raise ValueError("OpenAI API key not configured")

        results = []
        to_embed = []
        indices = []

        # Check cache for each text
        for i, text in enumerate(texts):
            cached = await self.cache.get(text)
            if cached is not None:
                results.append(cached)
            else:
                to_embed.append(text[:8000])
                indices.append(i)
                results.append(None)

        # Generate embeddings for uncached texts
        if to_embed:
            total_chars = sum(len(t) for t in to_embed)

            # Check budget
            if self.cost_tracker and not await self.cost_tracker.check_budget(
                    user_id, "embedding", total_chars
            ):
                raise ValueError("Daily budget limit exceeded")

            async with self.rate_limiter:
                try:
                    response = await self.client.embeddings.create(
                        model=Config.EMBEDDING_MODEL,
                        input=to_embed
                    )

                    # Store results
                    for idx, embedding_obj in zip(indices, response.data):
                        embedding = embedding_obj.embedding
                        results[idx] = embedding
                        await self.cache.set(texts[idx], embedding)

                    # Record cost
                    if self.cost_tracker:
                        await self.cost_tracker.record_cost(user_id, "embedding", total_chars)

                except Exception as e:
                    raise Exception(f"Batch embedding failed: {str(e)}")

        return results