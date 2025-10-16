"""
Smart Cache Warming System
Pre-loads frequently accessed embeddings to reduce latency
"""

import asyncio
from typing import List, Dict, Optional, Set
from pathlib import Path
import json
from datetime import datetime, timedelta
from collections import Counter

from src.config.settings import Config
from src.services.embeddings import EmbeddingService
from src.core.logging import logger


class CacheWarmer:
    """
    Intelligent cache warming for embeddings

    Features:
    - Tracks frequently accessed embeddings
    - Pre-loads popular queries on startup
    - Background warming during idle time
    - Analytics on cache hit rates
    """

    def __init__(
            self,
            embedding_service: EmbeddingService,
            analytics_dir: Optional[Path] = None
    ):
        self.embedding_service = embedding_service
        self.analytics_dir = analytics_dir or (Config.CACHE_DIR / "analytics")
        self.analytics_dir.mkdir(parents=True, exist_ok=True)

        self.access_log_file = self.analytics_dir / "embedding_access.jsonl"
        self.warming_config_file = self.analytics_dir / "warming_config.json"

        # In-memory tracking
        self.access_counts: Counter = Counter()
        self.recently_accessed: Set[str] = set()
        self.warming_in_progress = False

        # Load existing analytics
        self._load_analytics()

    def _load_analytics(self):
        """Load access analytics from disk"""
        try:
            if self.access_log_file.exists():
                # Load last 7 days of access logs
                cutoff_date = datetime.now() - timedelta(days=7)

                with open(self.access_log_file, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            access_time = datetime.fromisoformat(entry['timestamp'])

                            if access_time > cutoff_date:
                                text = entry['text']
                                count = entry.get('count', 1)
                                self.access_counts[text] += count
                        except Exception:
                            continue

                logger.info(
                    "cache_analytics_loaded",
                    unique_texts=len(self.access_counts),
                    total_accesses=sum(self.access_counts.values())
                )
        except Exception as e:
            logger.warning("cache_analytics_load_failed", error=str(e))

    async def log_access(self, text: str):
        """Log an embedding access for analytics"""
        try:
            self.access_counts[text] += 1
            self.recently_accessed.add(text)

            # Periodically write to disk (every 10 accesses)
            if len(self.recently_accessed) >= 10:
                await self._flush_access_log()
        except Exception as e:
            logger.warning("cache_access_log_failed", error=str(e))

    async def _flush_access_log(self):
        """Write access log to disk"""
        if not self.recently_accessed:
            return

        try:
            import aiofiles

            timestamp = datetime.now().isoformat()
            async with aiofiles.open(self.access_log_file, 'a') as f:
                for text in self.recently_accessed:
                    entry = {
                        'timestamp': timestamp,
                        'text': text,
                        'count': 1
                    }
                    await f.write(json.dumps(entry) + '\n')

            self.recently_accessed.clear()
            logger.debug("cache_access_log_flushed")
        except Exception as e:
            logger.warning("cache_access_log_flush_failed", error=str(e))

    def get_top_queries(self, n: int = 20) -> List[str]:
        """Get the N most frequently accessed queries"""
        return [text for text, _ in self.access_counts.most_common(n)]

    async def warm_cache(
            self,
            texts: Optional[List[str]] = None,
            top_n: int = 20,
            user_id: str = "cache_warmer"
    ):
        """
        Warm cache with specified texts or top N most accessed

        Args:
            texts: Specific texts to warm, or None to use top N
            top_n: Number of top queries to warm if texts not provided
            user_id: User ID for cost tracking
        """
        if self.warming_in_progress:
            logger.info("cache_warming_already_in_progress")
            return

        self.warming_in_progress = True

        try:
            # Determine what to warm
            if texts is None:
                texts = self.get_top_queries(top_n)

            if not texts:
                logger.info("cache_warming_no_queries_to_warm")
                return

            logger.info("cache_warming_start", count=len(texts))
            start_time = asyncio.get_event_loop().time()

            # Check which texts are already cached
            uncached = []
            cached_count = 0

            for text in texts:
                cached = await self.embedding_service.cache.get(text)
                if cached is None:
                    uncached.append(text)
                else:
                    cached_count += 1

            logger.info(
                "cache_warming_status",
                total=len(texts),
                already_cached=cached_count,
                to_warm=len(uncached)
            )

            # Warm uncached texts in batches
            if uncached:
                batch_size = 10
                for i in range(0, len(uncached), batch_size):
                    batch = uncached[i:i + batch_size]

                    try:
                        # Generate embeddings (will be cached automatically)
                        await self.embedding_service.embed_batch(batch, user_id)

                        # Small delay to avoid rate limits
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.error(
                            "cache_warming_batch_failed",
                            batch_start=i,
                            error=str(e)
                        )

            elapsed = asyncio.get_event_loop().time() - start_time
            logger.info(
                "cache_warming_complete",
                warmed=len(uncached),
                time_seconds=round(elapsed, 2)
            )

        except Exception as e:
            logger.error("cache_warming_failed", error=str(e))
        finally:
            self.warming_in_progress = False

    async def background_warming(
            self,
            interval_minutes: int = 60,
            top_n: int = 20
    ):
        """
        Run background cache warming periodically

        Args:
            interval_minutes: How often to run warming
            top_n: Number of top queries to warm
        """
        logger.info(
            "background_warming_started",
            interval_minutes=interval_minutes,
            top_n=top_n
        )

        while True:
            try:
                await asyncio.sleep(interval_minutes * 60)

                # Flush any pending access logs
                await self._flush_access_log()

                # Warm top queries
                await self.warm_cache(top_n=top_n)

            except asyncio.CancelledError:
                logger.info("background_warming_cancelled")
                break
            except Exception as e:
                logger.error("background_warming_error", error=str(e))
                # Continue despite errors

    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            "total_unique_queries": len(self.access_counts),
            "total_accesses": sum(self.access_counts.values()),
            "top_10_queries": self.get_top_queries(10),
            "warming_in_progress": self.warming_in_progress
        }

    async def save_warming_config(self, config: Dict):
        """Save warming configuration"""
        try:
            import aiofiles
            async with aiofiles.open(self.warming_config_file, 'w') as f:
                await f.write(json.dumps(config, indent=2))
            logger.info("warming_config_saved")
        except Exception as e:
            logger.error("warming_config_save_failed", error=str(e))

    async def load_warming_config(self) -> Optional[Dict]:
        """Load warming configuration"""
        try:
            if self.warming_config_file.exists():
                import aiofiles
                async with aiofiles.open(self.warming_config_file, 'r') as f:
                    content = await f.read()
                    return json.loads(content)
        except Exception as e:
            logger.error("warming_config_load_failed", error=str(e))
        return None


class SmartEmbeddingService:
    """
    Wrapper around EmbeddingService with cache warming

    Drop-in replacement that tracks accesses and enables warming
    """

    def __init__(self, *args, **kwargs):
        self.base_service = EmbeddingService(*args, **kwargs)
        self.cache_warmer = CacheWarmer(self.base_service)
        self._background_task: Optional[asyncio.Task] = None

    async def embed(self, text: str, user_id: str = "default") -> List[float]:
        """Generate embedding with access tracking"""
        # Log access for analytics
        await self.cache_warmer.log_access(text)

        # Generate embedding (uses cache automatically)
        return await self.base_service.embed(text, user_id)

    async def embed_batch(
            self,
            texts: List[str],
            user_id: str = "default"
    ) -> List[List[float]]:
        """Generate batch embeddings with access tracking"""
        # Log all accesses
        for text in texts:
            await self.cache_warmer.log_access(text)

        return await self.base_service.embed_batch(texts, user_id)

    def start_background_warming(
            self,
            interval_minutes: int = 60,
            top_n: int = 20
    ):
        """Start background cache warming task"""
        if self._background_task is None or self._background_task.done():
            self._background_task = asyncio.create_task(
                self.cache_warmer.background_warming(interval_minutes, top_n)
            )
            logger.info("background_warming_task_started")

    def stop_background_warming(self):
        """Stop background cache warming task"""
        if self._background_task and not self._background_task.done():
            self._background_task.cancel()
            logger.info("background_warming_task_stopped")

    async def warm_startup_cache(self, top_n: int = 20):
        """Warm cache on startup with top queries"""
        await self.cache_warmer.warm_cache(top_n=top_n)

    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return self.cache_warmer.get_cache_stats()

    # Proxy other attributes to base service
    def __getattr__(self, name):
        return getattr(self.base_service, name)


# ============================================================================
# Convenience Functions
# ============================================================================

async def initialize_smart_caching(
        embedding_service: EmbeddingService,
        warm_on_startup: bool = True,
        enable_background: bool = True,
        top_n: int = 20,
        interval_minutes: int = 60
) -> CacheWarmer:
    """
    Initialize smart caching with recommended settings

    Args:
        embedding_service: Base embedding service
        warm_on_startup: Warm cache immediately
        enable_background: Enable periodic background warming
        top_n: Number of top queries to warm
        interval_minutes: Background warming interval

    Returns:
        Configured CacheWarmer instance
    """
    warmer = CacheWarmer(embedding_service)

    if warm_on_startup:
        logger.info("warming_startup_cache", top_n=top_n)
        await warmer.warm_cache(top_n=top_n)

    if enable_background:
        asyncio.create_task(
            warmer.background_warming(interval_minutes, top_n)
        )

    return warmer