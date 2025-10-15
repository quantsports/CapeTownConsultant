"""
Caching utilities
LRU cache and persistent embedding cache
"""

import json
import hashlib
from pathlib import Path
from typing import Any, Optional, List
from collections import OrderedDict
from datetime import datetime
import aiofiles

from src.config.settings import Config


class LRUCache:
    """Simple LRU cache implementation"""

    def __init__(self, max_size: int = 1000):
        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def set(self, key: str, value: Any):
        """Set value in cache"""
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

    def clear(self):
        """Clear cache"""
        self.cache.clear()


class PersistentEmbeddingCache:
    """Disk-backed embedding cache with memory layer"""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Config.EMBEDDING_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.memory_cache = LRUCache(max_size=1000)

    def _cache_key(self, text: str) -> str:
        """Generate cache key from text"""
        return hashlib.md5(text.encode()).hexdigest()

    def _cache_file(self, key: str) -> Path:
        """Get cache file path"""
        return self.cache_dir / f"{key}.json"

    async def get(self, text: str) -> Optional[List[float]]:
        """Get embedding from cache"""
        key = self._cache_key(text)

        # Check memory cache first
        if cached := self.memory_cache.get(key):
            return cached

        # Check disk cache
        cache_file = self._cache_file(key)
        if cache_file.exists():
            try:
                async with aiofiles.open(cache_file, 'r') as f:
                    data = json.loads(await f.read())
                    embedding = data["embedding"]
                    self.memory_cache.set(key, embedding)
                    return embedding
            except Exception:
                pass

        return None

    async def set(self, text: str, embedding: List[float]):
        """Set embedding in cache"""
        key = self._cache_key(text)
        self.memory_cache.set(key, embedding)

        cache_file = self._cache_file(key)
        try:
            async with aiofiles.open(cache_file, 'w') as f:
                await f.write(json.dumps({
                    "embedding": embedding,
                    "timestamp": datetime.now().isoformat()
                }))
        except Exception:
            pass