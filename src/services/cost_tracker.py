"""
Cost tracking and budget management
UPDATED: Added Kagi FastGPT cost tracking
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Union
import aiofiles
import tiktoken

from src.config.settings import Config
from src.core.logging import logger


class CostTracker:
    """Track and manage API costs with enhanced logging"""

    # Cost per 1000 tokens or per call
    # UPDATED: Added Kagi search cost
    COSTS = {
        # OpenAI models (per 1000 tokens)
        "gpt-4o-input": 0.0025,
        "gpt-4o-output": 0.01,
        "gpt-4o-mini-input": 0.000150,
        "gpt-4o-mini-output": 0.000600,

        # Embeddings (per 1000 tokens)
        "embedding": 0.00002,

        # Search APIs (per call)
        "serpapi": 0.002,
        "google-search": 0.005,
        "perplexity": 0.001,  # Per 1000 tokens for Perplexity
        "kagi-search": 0.015,  # NEW: $0.015 per query (flat rate)
    }

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = storage_dir or str(Config.COST_DIR)
        os.makedirs(self.storage_dir, exist_ok=True)

        # In-memory cache
        self.user_costs: Dict[str, float] = {}
        self.daily_limits: Dict[str, float] = {}

        # Cache encoder failures to avoid repeated errors
        self._encoder_cache: Dict[str, Optional[tiktoken.Encoding]] = {}
        self._failed_encoders: set = set()

    def _cost_file(self, user_id: str) -> str:
        """Get cost file path for user and current date"""
        safe_id = hashlib.md5(user_id.encode()).hexdigest()
        date_str = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.storage_dir, f"{safe_id}_{date_str}.json")

    async def load_user_costs(self, user_id: str):
        """Load user costs for current day"""
        if user_id in self.user_costs:
            return

        cost_file = self._cost_file(user_id)
        if os.path.exists(cost_file):
            try:
                async with aiofiles.open(cost_file, 'r') as f:
                    content = await f.read()
                    data = json.loads(content)
                    self.user_costs[user_id] = data.get("total", 0.0)
                    self.daily_limits[user_id] = data.get("limit", Config.DAILY_BUDGET_LIMIT)
            except Exception as e:
                logger.error("cost_load_failed", user_id=user_id, error=str(e))
                self.user_costs[user_id] = 0.0
        else:
            self.user_costs[user_id] = 0.0

    async def save_user_costs(self, user_id: str):
        """Save user costs to disk"""
        cost_file = self._cost_file(user_id)
        data = {
            "user_id": user_id,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total": self.user_costs.get(user_id, 0.0),
            "limit": self.daily_limits.get(user_id, Config.DAILY_BUDGET_LIMIT),
            "updated_at": datetime.now().isoformat()
        }

        try:
            async with aiofiles.open(cost_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            logger.error("cost_save_failed", user_id=user_id, error=str(e))

    def _get_encoder(self, model: str) -> Optional[tiktoken.Encoding]:
        """Get tiktoken encoder for model with caching and error handling"""
        # Check cache first
        if model in self._encoder_cache:
            return self._encoder_cache[model]

        # Check if we've already failed for this model
        if model in self._failed_encoders:
            return None

        try:
            encoder = tiktoken.encoding_for_model(model)
            self._encoder_cache[model] = encoder
            return encoder
        except KeyError:
            logger.error(
                "encoder_not_found",
                model=model,
                message=f"No tiktoken encoder found for model '{model}'. Using fallback estimation.",
                severity="error"
            )
            # Cache the failure to avoid repeated logs
            self._failed_encoders.add(model)
            self._encoder_cache[model] = None
            return None

    def count_tokens(
        self,
        text: Union[str, List[Dict]],
        model: str = "gpt-4o"
    ) -> int:
        """Count tokens in text or message list using tiktoken"""
        encoder = self._get_encoder(model)

        if encoder is None:
            # Fallback with explicit warning
            if isinstance(text, str):
                estimated = len(text) // 4
            else:
                total = sum(len(str(m.get("content", ""))) for m in text if isinstance(m, dict))
                estimated = total // 4

            logger.warning(
                "using_fallback_token_estimation",
                model=model,
                estimated_tokens=estimated,
                message="Using character-based approximation (chars/4)"
            )
            return estimated

        # Use actual encoder
        if isinstance(text, str):
            return len(encoder.encode(text))

        if isinstance(text, list):
            num_tokens = 0
            for message in text:
                if isinstance(message, dict):
                    # Add message overhead (approximately 4 tokens per message)
                    num_tokens += 4
                    # Count tokens in content
                    content = message.get("content", "")
                    if isinstance(content, str):
                        num_tokens += len(encoder.encode(content))
                    # Count tokens in role
                    role = message.get("role", "")
                    if role:
                        num_tokens += len(encoder.encode(role))
                    # Count tokens in name if present
                    name = message.get("name", "")
                    if name:
                        num_tokens += len(encoder.encode(name))
            # Add overhead for reply priming
            num_tokens += 2
            return num_tokens

        return 0

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str
    ) -> float:
        """Calculate cost based on token counts"""
        # Normalize model name (remove version suffixes)
        model_base = model.split("-20")[0]  # Remove date suffixes like -2024-08-06

        input_cost = self.COSTS.get(f"{model_base}-input", 0.0) * input_tokens
        output_cost = self.COSTS.get(f"{model_base}-output", 0.0) * output_tokens

        return input_cost + output_cost

    def estimate_cost(self, operation: str, units: int = 1) -> float:
        """
        Estimate cost for an operation

        Args:
            operation: Operation type (e.g., 'gpt-4o-input', 'serpapi', 'kagi-search')
            units: Number of units (tokens or calls)

        Returns:
            Estimated cost
        """
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
        """
        Record cost for an operation

        Args:
            user_id: User identifier
            operation: Operation type (e.g., 'kagi-search', 'serpapi')
            units: Number of units
        """
        if not Config.ENABLE_COST_TRACKING:
            return

        cost = self.estimate_cost(operation, units)
        self.user_costs[user_id] = self.user_costs.get(user_id, 0.0) + cost
        await self.save_user_costs(user_id)

    async def record_completion_cost(
        self,
        user_id: str,
        messages: Union[str, List[Dict]],
        completion: str,
        model: str
    ):
        """Record cost for a chat completion with accurate token counting"""
        if not Config.ENABLE_COST_TRACKING:
            return

        # Count tokens accurately
        input_tokens = self.count_tokens(messages, model)
        output_tokens = self.count_tokens(completion, model)

        # Calculate cost
        cost = self.calculate_cost(input_tokens, output_tokens, model)

        # Record cost
        self.user_costs[user_id] = self.user_costs.get(user_id, 0.0) + cost
        await self.save_user_costs(user_id)

        logger.info(
            "completion_cost_recorded",
            user_id=user_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        )

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

    async def get_daily_total(self, user_id: str) -> float:
        """Get total daily cost for a user"""
        await self.load_user_costs(user_id)
        return self.user_costs.get(user_id, 0.0)

    def estimate_completion_cost(
        self,
        messages: Union[str, List[Dict]],
        estimated_output_tokens: int,
        model: str
    ) -> float:
        """Estimate cost for a completion before making the API call"""
        input_tokens = self.count_tokens(messages, model)
        return self.calculate_cost(input_tokens, estimated_output_tokens, model)

    def get_token_estimate(
        self,
        text: Union[str, List[Dict]],
        model: str = "gpt-4o"
    ) -> Dict[str, int]:
        """Get token count estimate for text"""
        tokens = self.count_tokens(text, model)
        chars = len(text) if isinstance(text, str) else sum(
            len(str(m.get("content", ""))) for m in text if isinstance(m, dict)
        )

        return {
            "tokens": tokens,
            "characters": chars,
            "ratio": chars / tokens if tokens > 0 else 0
        }