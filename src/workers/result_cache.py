"""
Worker result caching system for performance optimization
Caches worker results to avoid redundant computation
Version: 1.0.0
"""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import hashlib
import json

from src.core.logging import logger
from src.workers.worker import WorkerResult
from src.workers.templates import WorkerType


@dataclass
class CacheEntry:
    """Cached worker result with metadata"""
    result: WorkerResult
    created_at: datetime
    hit_count: int = 0
    last_accessed: Optional[datetime] = None


class WorkerResultCache:
    """
    Cache for worker results to improve performance and reduce costs

    Features:
    - TTL-based expiration
    - LRU eviction
    - Query-based cache keys
    - Deduplication
    """

    def __init__(
        self,
        max_size: int = 100,
        ttl_seconds: int = 3600,
        enable_cache: bool = True
    ):
        """
        Initialize result cache

        Args:
            max_size: Maximum number of cached results
            ttl_seconds: Time-to-live for cache entries in seconds
            enable_cache: Whether caching is enabled
        """
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.ttl = timedelta(seconds=ttl_seconds)
        self.enable_cache = enable_cache
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "invalidations": 0
        }

    def _generate_cache_key(
        self,
        worker_type: WorkerType,
        query: str,
        context_hash: Optional[str] = None
    ) -> str:
        """
        Generate cache key for a worker execution

        Args:
            worker_type: Type of worker
            query: User query
            context_hash: Optional hash of context data

        Returns:
            Cache key string
        """
        # Create composite key from worker type and query
        key_parts = [
            worker_type.value,
            query.lower().strip()
        ]

        if context_hash:
            key_parts.append(context_hash)

        key_string = "|".join(key_parts)

        # Generate hash for consistent key length
        return hashlib.sha256(key_string.encode()).hexdigest()[:32]

    def get(
        self,
        worker_type: WorkerType,
        query: str,
        context_hash: Optional[str] = None
    ) -> Optional[WorkerResult]:
        """
        Retrieve cached result if available and valid

        Args:
            worker_type: Type of worker
            query: User query
            context_hash: Optional context hash

        Returns:
            Cached WorkerResult or None if not found/expired
        """
        if not self.enable_cache:
            return None

        cache_key = self._generate_cache_key(worker_type, query, context_hash)

        if cache_key not in self.cache:
            self.stats["misses"] += 1
            logger.debug("cache_miss", worker=worker_type.value, key=cache_key[:8])
            return None

        entry = self.cache[cache_key]

        # Check if expired
        age = datetime.now() - entry.created_at
        if age > self.ttl:
            logger.debug("cache_expired", worker=worker_type.value, age_seconds=age.total_seconds())
            self._remove(cache_key)
            self.stats["misses"] += 1
            return None

        # Update access metadata
        entry.hit_count += 1
        entry.last_accessed = datetime.now()
        self.stats["hits"] += 1

        logger.info(
            "cache_hit",
            worker=worker_type.value,
            age_seconds=age.total_seconds(),
            hit_count=entry.hit_count
        )

        return entry.result

    def put(
        self,
        worker_type: WorkerType,
        query: str,
        result: WorkerResult,
        context_hash: Optional[str] = None
    ):
        """
        Store result in cache

        Args:
            worker_type: Type of worker
            query: User query
            result: Worker result to cache
            context_hash: Optional context hash
        """
        if not self.enable_cache or not result.success:
            # Don't cache failed results
            return

        cache_key = self._generate_cache_key(worker_type, query, context_hash)

        # Check if we need to evict
        if len(self.cache) >= self.max_size and cache_key not in self.cache:
            self._evict_lru()

        entry = CacheEntry(
            result=result,
            created_at=datetime.now(),
            hit_count=0,
            last_accessed=None
        )

        self.cache[cache_key] = entry

        logger.debug(
            "cache_stored",
            worker=worker_type.value,
            key=cache_key[:8],
            cache_size=len(self.cache)
        )

    def _evict_lru(self):
        """Evict least recently used cache entry"""
        if not self.cache:
            return

        # Find LRU entry
        lru_key = None
        lru_time = datetime.now()

        for key, entry in self.cache.items():
            access_time = entry.last_accessed or entry.created_at
            if access_time < lru_time:
                lru_time = access_time
                lru_key = key

        if lru_key:
            self._remove(lru_key)
            self.stats["evictions"] += 1
            logger.debug("cache_evicted", key=lru_key[:8])

    def _remove(self, cache_key: str):
        """Remove entry from cache"""
        if cache_key in self.cache:
            del self.cache[cache_key]

    def invalidate(
        self,
        worker_type: Optional[WorkerType] = None,
        query: Optional[str] = None
    ):
        """
        Invalidate cache entries

        Args:
            worker_type: If provided, only invalidate this worker type
            query: If provided, only invalidate this query
        """
        if worker_type is None and query is None:
            # Clear all
            count = len(self.cache)
            self.cache.clear()
            self.stats["invalidations"] += count
            logger.info("cache_cleared", count=count)
            return

        # Selective invalidation
        keys_to_remove = []

        for key in self.cache.keys():
            # Since we hash the keys, we can't easily filter
            # For now, just clear all if worker_type or query specified
            # In production, we'd want a more sophisticated indexing system
            keys_to_remove.append(key)

        for key in keys_to_remove:
            self._remove(key)
            self.stats["invalidations"] += 1

        logger.info(
            "cache_invalidated",
            count=len(keys_to_remove),
            worker=worker_type.value if worker_type else "all"
        )

    def get_stats(self) -> Dict:
        """
        Get cache statistics

        Returns:
            Dictionary with cache metrics
        """
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (
            self.stats["hits"] / total_requests
            if total_requests > 0
            else 0.0
        )

        return {
            **self.stats,
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "cache_size": len(self.cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl.total_seconds(),
            "enabled": self.enable_cache
        }

    def get_cache_info(self) -> List[Dict]:
        """
        Get information about cached entries

        Returns:
            List of cache entry information
        """
        info = []

        for key, entry in self.cache.items():
            age = datetime.now() - entry.created_at
            info.append({
                "key": key[:8],  # Shortened for display
                "worker_type": entry.result.worker_type.value,
                "age_seconds": age.total_seconds(),
                "hit_count": entry.hit_count,
                "confidence": entry.result.confidence,
                "last_accessed": (
                    entry.last_accessed.isoformat()
                    if entry.last_accessed
                    else None
                )
            })

        # Sort by hit count descending
        info.sort(key=lambda x: x["hit_count"], reverse=True)

        return info

    def warm_up(
        self,
        worker_type: WorkerType,
        common_queries: List[str]
    ):
        """
        Pre-populate cache with common queries (would need actual execution)

        Args:
            worker_type: Worker type to warm up
            common_queries: List of common queries
        """
        logger.info(
            "cache_warmup_requested",
            worker=worker_type.value,
            query_count=len(common_queries)
        )
        # Note: Actual warm-up would require executing workers
        # This is a placeholder for the interface

    def export_stats(self) -> str:
        """
        Export cache statistics as JSON

        Returns:
            JSON string with stats
        """
        stats = self.get_stats()
        return json.dumps(stats, indent=2)
