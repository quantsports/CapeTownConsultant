"""
User profile management
Persistent storage of user preferences and metadata with enhanced reliability
"""

import os
import json
import hashlib
import asyncio
import time
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple
import aiofiles
import aiofiles.os
from datetime import datetime

from src.config.settings import Config
from src.core.logging import logger


class ProfileManager:
    """Manage user profiles with disk persistence, caching, and concurrency control"""

    def __init__(
            self,
            storage_dir: Optional[str] = None,
            cache_size: int = 1000,
            cache_ttl: int = 3600  # 1 hour
    ):
        self.storage_dir = storage_dir or str(Config.PROFILE_DIR)
        os.makedirs(self.storage_dir, exist_ok=True)

        # LRU cache with TTL
        self.cache: OrderedDict[str, Dict] = OrderedDict()
        self.cache_timestamps: Dict[str, float] = {}
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl

        # Per-user locks for write safety
        self._locks: Dict[str, asyncio.Lock] = {}

    def _profile_path(self, user_id: str) -> str:
        """Get profile file path for user"""
        safe_id = hashlib.md5(user_id.encode()).hexdigest()
        return os.path.join(self.storage_dir, f"{safe_id}.json")

    def _get_lock(self, user_id: str) -> asyncio.Lock:
        """Get or create lock for user"""
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()
        return self._locks[user_id]

    def _is_cache_valid(self, user_id: str) -> bool:
        """Check if cached entry is still valid"""
        if user_id not in self.cache_timestamps:
            return False
        age = time.time() - self.cache_timestamps[user_id]
        return age < self.cache_ttl

    def _add_to_cache(self, user_id: str, profile: Dict):
        """Add to cache with LRU eviction"""
        # Remove if exists (for reordering)
        if user_id in self.cache:
            del self.cache[user_id]
            del self.cache_timestamps[user_id]

        # Evict oldest if at capacity
        if len(self.cache) >= self.cache_size:
            oldest_id = next(iter(self.cache))
            del self.cache[oldest_id]
            del self.cache_timestamps[oldest_id]
            if oldest_id in self._locks and not self._locks[oldest_id].locked():
                del self._locks[oldest_id]  # Clean up unused locks

        # Add new entry
        self.cache[user_id] = profile
        self.cache_timestamps[user_id] = time.time()

    def _validate_profile_data(self, data: Dict) -> Tuple[bool, Optional[str]]:
        """Validate profile data before storage"""
        if not isinstance(data, dict):
            return False, "Data must be a dictionary"

        # Check for empty keys
        if any(not k or not isinstance(k, str) for k in data.keys()):
            return False, "All keys must be non-empty strings"

        # Estimate size (rough check)
        try:
            serialized = json.dumps(data)
            if len(serialized) > 1_000_000:  # 1MB limit
                return False, f"Profile data too large: {len(serialized)} bytes"
        except (TypeError, ValueError) as e:
            return False, f"Data not JSON serializable: {e}"

        return True, None

    async def read(
            self,
            user_id: str,
            keys: Optional[List[str]] = None
    ) -> Dict:
        """Read user profile with TTL-aware caching"""
        # Check cache with TTL validation
        if user_id in self.cache and self._is_cache_valid(user_id):
            # Move to end (LRU)
            self.cache.move_to_end(user_id)
            profile = self.cache[user_id]
        else:
            # Load from disk
            path = self._profile_path(user_id)
            if os.path.exists(path):
                try:
                    async with aiofiles.open(path, 'r') as f:
                        content = await f.read()
                        profile = json.loads(content)
                        self._add_to_cache(user_id, profile)
                except Exception as e:
                    logger.error("profile_read_failed", user_id=user_id, error=str(e))
                    # Clear stale cache entry
                    if user_id in self.cache:
                        del self.cache[user_id]
                        del self.cache_timestamps[user_id]
                    profile = {}
            else:
                profile = {}

        # Return specific keys if requested
        if keys:
            return {k: profile.get(k) for k in keys if k in profile}
        return profile.copy()  # Return copy to prevent cache mutation

    async def write(self, user_id: str, data: Dict) -> bool:
        """Update user profile with validation and atomic writes"""
        # Validate input
        is_valid, error = self._validate_profile_data(data)
        if not is_valid:
            logger.warning("profile_validation_failed", user_id=user_id, error=error)
            return False

        async with self._get_lock(user_id):
            try:
                # Read existing profile
                profile = await self.read(user_id)

                # Update with new data
                profile.update(data)

                # Write to disk atomically
                path = self._profile_path(user_id)
                temp_path = f"{path}.tmp"

                async with aiofiles.open(temp_path, 'w') as f:
                    await f.write(json.dumps(profile, indent=2))

                # Atomic rename
                os.replace(temp_path, path)

                # Update cache
                self._add_to_cache(user_id, profile)

                logger.info("profile_updated", user_id=user_id, keys=list(data.keys()))
                return True

            except Exception as e:
                logger.error("profile_write_failed", user_id=user_id, error=str(e))
                # Clean up temp file if exists
                temp_path = f"{self._profile_path(user_id)}.tmp"
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
                return False

    async def delete(self, user_id: str, backup: bool = True) -> bool:
        """Delete user profile with optional backup"""
        async with self._get_lock(user_id):
            try:
                path = self._profile_path(user_id)

                if os.path.exists(path):
                    # Create backup if requested
                    if backup:
                        backup_dir = os.path.join(self.storage_dir, "_backups")
                        os.makedirs(backup_dir, exist_ok=True)

                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        backup_path = os.path.join(
                            backup_dir,
                            f"{os.path.basename(path)}.{timestamp}.bak"
                        )

                        # Async copy
                        async with aiofiles.open(path, 'rb') as src:
                            async with aiofiles.open(backup_path, 'wb') as dst:
                                await dst.write(await src.read())

                        logger.info("profile_backed_up", user_id=user_id, backup_path=backup_path)

                    # Delete original
                    os.remove(path)

                # Clear cache
                if user_id in self.cache:
                    del self.cache[user_id]
                    del self.cache_timestamps[user_id]

                logger.info("profile_deleted", user_id=user_id)
                return True

            except Exception as e:
                logger.error("profile_delete_failed", user_id=user_id, error=str(e))
                return False

    def get_cache_stats(self) -> Dict:
        """Get cache statistics for monitoring"""
        return {
            "size": len(self.cache),
            "capacity": self.cache_size,
            "ttl_seconds": self.cache_ttl,
            "users_cached": list(self.cache.keys())
        }

    def clear_cache(self, user_id: Optional[str] = None):
        """Clear cache for specific user or all users"""
        if user_id:
            if user_id in self.cache:
                del self.cache[user_id]
                del self.cache_timestamps[user_id]
                logger.info("cache_cleared", user_id=user_id)
        else:
            self.cache.clear()
            self.cache_timestamps.clear()
            logger.info("cache_cleared_all")