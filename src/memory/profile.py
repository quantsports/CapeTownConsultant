"""
User profile management
Persistent storage of user preferences and metadata with enhanced reliability
FIXES: Critical #1 - Race condition in lock creation
FIXES: Medium #11 - Cache stampede on reads
FIXES: Medium #12 - Unclosed temp files
"""

import os
import json
import hashlib
import asyncio
import time
import traceback
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

        # CRITICAL FIX #1: Master lock for lock creation (prevents race condition)
        self._master_lock = asyncio.Lock()

        # Per-user locks for write safety
        self._write_locks: Dict[str, asyncio.Lock] = {}

        # MEDIUM FIX #11: Per-user read locks to prevent cache stampede
        self._read_locks: Dict[str, asyncio.Lock] = {}

    def _profile_path(self, user_id: str) -> str:
        """Get profile file path for user"""
        safe_id = hashlib.md5(user_id.encode()).hexdigest()
        return os.path.join(self.storage_dir, f"{safe_id}.json")

    async def _get_write_lock(self, user_id: str) -> asyncio.Lock:
        """
        Get or create write lock for user (thread-safe)
        CRITICAL FIX #1: Guarded by master lock to prevent race conditions
        """
        async with self._master_lock:
            if user_id not in self._write_locks:
                self._write_locks[user_id] = asyncio.Lock()
            return self._write_locks[user_id]

    async def _get_read_lock(self, user_id: str) -> asyncio.Lock:
        """
        Get or create read lock for user (prevents cache stampede)
        MEDIUM FIX #11: Ensures only one read per user hits disk at a time
        """
        async with self._master_lock:
            if user_id not in self._read_locks:
                self._read_locks[user_id] = asyncio.Lock()
            return self._read_locks[user_id]

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

            # Clean up unused locks
            if oldest_id in self._write_locks and not self._write_locks[oldest_id].locked():
                del self._write_locks[oldest_id]
            if oldest_id in self._read_locks and not self._read_locks[oldest_id].locked():
                del self._read_locks[oldest_id]

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
        """
        Read user profile with TTL-aware caching
        MEDIUM FIX #11: Use read lock to prevent cache stampede
        """
        # MEDIUM FIX #11: Acquire read lock to prevent parallel reads
        read_lock = await self._get_read_lock(user_id)
        async with read_lock:
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
        """
        Update user profile with validation and atomic writes
        MEDIUM FIX #12: Properly cleanup temp files
        """
        # Validate input
        is_valid, error = self._validate_profile_data(data)
        if not is_valid:
            logger.warning("profile_validation_failed", user_id=user_id, error=error)
            return False

        write_lock = await self._get_write_lock(user_id)
        async with write_lock:
            try:
                # Read existing profile
                profile = await self.read(user_id)

                # Update with new data
                profile.update(data)
                profile["last_updated"] = datetime.now().isoformat()

                # Write atomically using temp file
                path = self._profile_path(user_id)
                temp_path = f"{path}.tmp"

                # MEDIUM FIX #12: Ensure temp file cleanup in all cases
                try:
                    async with aiofiles.open(temp_path, 'w') as f:
                        await f.write(json.dumps(profile, indent=2))

                    # Atomic rename
                    await aiofiles.os.replace(temp_path, path)

                    # Update cache
                    self._add_to_cache(user_id, profile)

                    logger.info("profile_updated", user_id=user_id, keys=len(data))
                    return True

                except Exception as write_error:
                    # MEDIUM FIX #12: Clean up temp file on error
                    try:
                        if os.path.exists(temp_path):
                            await aiofiles.os.remove(temp_path)
                    except Exception as cleanup_error:
                        logger.warning(
                            "temp_file_cleanup_failed",
                            user_id=user_id,
                            error=str(cleanup_error)
                        )
                    raise write_error

            except Exception as e:
                logger.error(
                    "profile_write_failed",
                    user_id=user_id,
                    error=str(e),
                    traceback=traceback.format_exc()
                )
                return False

    async def delete(self, user_id: str) -> bool:
        """Delete user profile"""
        write_lock = await self._get_write_lock(user_id)
        async with write_lock:
            try:
                path = self._profile_path(user_id)
                if os.path.exists(path):
                    await aiofiles.os.remove(path)

                # Clear from cache
                if user_id in self.cache:
                    del self.cache[user_id]
                    del self.cache_timestamps[user_id]

                logger.info("profile_deleted", user_id=user_id)
                return True

            except Exception as e:
                logger.error("profile_delete_failed", user_id=user_id, error=str(e))
                return False

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            "cache_size": len(self.cache),
            "cache_limit": self.cache_size,
            "cache_ttl": self.cache_ttl,
            "write_locks": len(self._write_locks),
            "read_locks": len(self._read_locks),
        }