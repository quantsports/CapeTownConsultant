"""
User profile management
Persistent storage of user preferences and metadata
"""

import os
import json
import hashlib
from typing import Dict, List, Optional
import aiofiles

from src.config.settings import Config
from src.core.logging import logger


class ProfileManager:
    """Manage user profiles with disk persistence"""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = storage_dir or str(Config.PROFILE_DIR)
        os.makedirs(self.storage_dir, exist_ok=True)
        self.cache: Dict[str, Dict] = {}

    def _profile_path(self, user_id: str) -> str:
        """Get profile file path for user"""
        safe_id = hashlib.md5(user_id.encode()).hexdigest()
        return os.path.join(self.storage_dir, f"{safe_id}.json")

    async def read(
            self,
            user_id: str,
            keys: Optional[List[str]] = None
    ) -> Dict:
        """Read user profile"""
        # Check cache first
        if user_id in self.cache:
            profile = self.cache[user_id]
        else:
            path = self._profile_path(user_id)
            if os.path.exists(path):
                try:
                    async with aiofiles.open(path, 'r') as f:
                        content = await f.read()
                        profile = json.loads(content)
                        self.cache[user_id] = profile
                except Exception as e:
                    logger.error("profile_read_failed", user_id=user_id, error=str(e))
                    profile = {}
            else:
                profile = {}

        # Return specific keys if requested
        if keys:
            return {k: profile.get(k) for k in keys if k in profile}
        return profile

    async def write(self, user_id: str, data: Dict) -> bool:
        """Update user profile"""
        try:
            # Read existing profile
            profile = await self.read(user_id)

            # Update with new data
            profile.update(data)
            self.cache[user_id] = profile

            # Write to disk
            path = self._profile_path(user_id)
            async with aiofiles.open(path, 'w') as f:
                await f.write(json.dumps(profile, indent=2))

            logger.info("profile_updated", user_id=user_id, keys=list(data.keys()))
            return True

        except Exception as e:
            logger.error("profile_write_failed", user_id=user_id, error=str(e))
            return False

    async def delete(self, user_id: str) -> bool:
        """Delete user profile"""
        try:
            path = self._profile_path(user_id)
            if os.path.exists(path):
                os.remove(path)

            if user_id in self.cache:
                del self.cache[user_id]

            logger.info("profile_deleted", user_id=user_id)
            return True

        except Exception as e:
            logger.error("profile_delete_failed", user_id=user_id, error=str(e))
            return False