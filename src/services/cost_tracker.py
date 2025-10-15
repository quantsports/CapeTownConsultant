"""
Cost tracking service
Track and limit API costs per user
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict
import aiofiles

from src.config.settings import Config
from src.core.logging import logger


class CostTracker:
    """Track and limit API costs per user"""

    COSTS = {
        "gpt-4o-input": 2.50 / 1_000_000,
        "gpt-4o-output": 10.00 / 1_000_000,
        "gpt-4o-mini-input": 0.15 / 1_000_000,
        "gpt-4o-mini-output": 0.60 / 1_000_000,
        "embedding": 0.02 / 1_000_000,
        "serpapi": 0.002,
        "perplexity": 0.001,
        "google-search": 0.005,
    }

    def __init__(self, storage_dir: Path = None):
        self.storage_dir = storage_dir or (Config.CACHE_DIR / "costs")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.user_costs: Dict[str, float] = {}
        self.daily_limits: Dict[str, float] = {}

    def _cost_file(self, user_id: str) -> Path:
        """Get cost file path for user and today"""
        safe_id = hashlib.md5(user_id.encode()).hexdigest()
        today = datetime.now().strftime("%Y-%m-%d")
        return self.storage_dir / f"{safe_id}_{today}.json"

    async def load_user_costs(self, user_id: str):
        """Load costs from disk"""
        cost_file = self._cost_file(user_id)
        if cost_file.exists():
            try:
                async with aiofiles.open(cost_file, 'r') as f:
                    data = json.loads(await f.read())
                    self.user_costs[user_id] = data.get("total", 0.0)
            except Exception as e:
                logger.error("cost_load_failed", user_id=user_id, error=str(e))
                self.user_costs[user_id] = 0.0
        else:
            self.user_costs[user_id] = 0.0

    async def save_user_costs(self, user_id: str):
        """Save costs to disk"""
        cost_file = self._cost_file(user_id)
        try:
            async with aiofiles.open(cost_file, 'w') as f:
                await f.write(json.dumps({
                    "total": self.user_costs.get(user_id, 0.0),
                    "timestamp": datetime.now().isoformat()
                }))
        except Exception as e:
            logger.error("cost_save_failed", user_id=user_id, error=str(e))

    def estimate_cost(self, operation: str, units: int = 1) -> float:
        """Estimate cost for an operation"""
        return self.COSTS.get(operation, 0.0) * units

    async def check_budget(self, user_id: str, operation: str, units: int = 1) -> bool:
        """Check if operation is within budget"""
        if not Config.ENABLE_COST_TRACKING:
            return True

        await self.load_user_costs(user_id)
        current = self.user_costs.get(user_id, 0.0)
        limit = self.daily_limits.get(user_id, Config.DAILY_BUDGET_LIMIT)
        estimated_cost = self.estimate_cost(operation, units)

        return (current + estimated_cost) < limit

    async def record_cost(self, user_id: str, operation: str, units: int = 1):
        """Record cost for an operation"""
        if not Config.ENABLE_COST_TRACKING:
            return

        cost = self.estimate_cost(operation, units)
        self.user_costs[user_id] = self.user_costs.get(user_id, 0.0) + cost
        await self.save_user_costs(user_id)

    async def get_user_costs(self, user_id: str) -> Dict[str, float]:
        """Get user cost summary"""
        await self.load_user_costs(user_id)
        limit = self.daily_limits.get(user_id, Config.DAILY_BUDGET_LIMIT)
        current = self.user_costs.get(user_id, 0.0)

        return {
            "total": current,
            "limit": limit,
            "remaining": max(0, limit - current)
        }