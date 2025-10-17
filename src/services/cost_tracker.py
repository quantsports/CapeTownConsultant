"""
Cost tracking service
Track and limit API costs per user with accurate token counting
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Union, Optional
import aiofiles

try:
    import tiktoken
except ImportError:
    tiktoken = None

from src.config.settings import Config
from src.core.logging import logger


class CostTracker:
    """Track and limit API costs per user with accurate tiktoken-based token counting"""

    # Pricing per million tokens (as of January 2025)
    COSTS = {
        "gpt-4o-input": 2.50 / 1_000_000,
        "gpt-4o-output": 10.00 / 1_000_000,
        "gpt-4o-mini-input": 0.15 / 1_000_000,
        "gpt-4o-mini-output": 0.60 / 1_000_000,
        "gpt-4-turbo-input": 10.00 / 1_000_000,
        "gpt-4-turbo-output": 30.00 / 1_000_000,
        "gpt-3.5-turbo-input": 0.50 / 1_000_000,
        "gpt-3.5-turbo-output": 1.50 / 1_000_000,
        "text-embedding-3-small": 0.02 / 1_000_000,
        "text-embedding-3-large": 0.13 / 1_000_000,
        "text-embedding-ada-002": 0.10 / 1_000_000,
        "serpapi": 0.002,
        "perplexity": 0.001,
        "google-search": 0.005,
    }

    # Model to encoding mapping
    MODEL_ENCODINGS = {
        "gpt-4o": "o200k_base",
        "gpt-4o-mini": "o200k_base",
        "gpt-4-turbo": "cl100k_base",
        "gpt-4": "cl100k_base",
        "gpt-3.5-turbo": "cl100k_base",
        "text-embedding-3-small": "cl100k_base",
        "text-embedding-3-large": "cl100k_base",
        "text-embedding-ada-002": "cl100k_base",
    }

    def __init__(self, storage_dir: Path = None):
        self.storage_dir = storage_dir or (Config.CACHE_DIR / "costs")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.user_costs: Dict[str, float] = {}
        self.daily_limits: Dict[str, float] = {}
        self._encoders: Dict[str, any] = {}  # Cache for tiktoken encoders

        # Warn if tiktoken not available
        if tiktoken is None:
            logger.warning("tiktoken_not_installed",
                          message="tiktoken not available, falling back to approximate token counting")

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

    def _get_encoder(self, model: str):
        """Get or create tiktoken encoder for model"""
        if tiktoken is None:
            return None

        if model not in self._encoders:
            try:
                # Try to get encoding for the model
                encoding_name = self.MODEL_ENCODINGS.get(model)
                if encoding_name:
                    self._encoders[model] = tiktoken.get_encoding(encoding_name)
                else:
                    # Fallback: try to get encoding directly from model name
                    self._encoders[model] = tiktoken.encoding_for_model(model)
            except Exception as e:
                logger.warning("encoder_creation_failed", model=model, error=str(e))
                return None

        return self._encoders[model]

    def count_tokens(
        self,
        text: Union[str, List[Dict]],
        model: str = "gpt-4o"
    ) -> int:
        """
        Count tokens in text or messages using tiktoken

        Args:
            text: String or list of message dicts
            model: Model name for appropriate encoding

        Returns:
            Token count
        """
        encoder = self._get_encoder(model)

        # Fallback to approximate counting if tiktoken unavailable
        if encoder is None:
            if isinstance(text, str):
                # Rough approximation: 1 token ≈ 4 characters
                return len(text) // 4
            elif isinstance(text, list):
                # Count all message content
                total = 0
                for msg in text:
                    if isinstance(msg, dict):
                        content = msg.get("content", "")
                        if isinstance(content, str):
                            total += len(content) // 4
                return total
            return 0

        # Count tokens with tiktoken
        if isinstance(text, str):
            return len(encoder.encode(text))
        elif isinstance(text, list):
            # Count tokens in message format (OpenAI chat completion format)
            # Each message has overhead: role, content, etc.
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
        """
        Calculate cost based on token counts

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name

        Returns:
            Total cost in dollars
        """
        # Normalize model name (remove version suffixes)
        model_base = model.split("-20")[0]  # Remove date suffixes like -2024-08-06

        input_cost = self.COSTS.get(f"{model_base}-input", 0.0) * input_tokens
        output_cost = self.COSTS.get(f"{model_base}-output", 0.0) * output_tokens

        return input_cost + output_cost

    def estimate_cost(self, operation: str, units: int = 1) -> float:
        """
        Estimate cost for an operation (legacy method for backward compatibility)

        Args:
            operation: Operation type (e.g., 'gpt-4o-input', 'serpapi')
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
        Record cost for an operation (legacy method for backward compatibility)

        Args:
            user_id: User identifier
            operation: Operation type
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
        """
        Record cost for a chat completion with accurate token counting

        Args:
            user_id: User identifier
            messages: Input messages (string or message list)
            completion: Output completion text
            model: Model name used
        """
        if not Config.ENABLE_COST_TRACKING:
            return

        # Count tokens accurately
        input_tokens = self.count_tokens(messages, model)
        output_tokens = self.count_tokens(completion, model)

        # Calculate cost
        cost = self.calculate_cost(input_tokens, output_tokens, model)

        # Record it
        self.user_costs[user_id] = self.user_costs.get(user_id, 0.0) + cost
        await self.save_user_costs(user_id)

        logger.debug(
            "cost_recorded",
            user_id=user_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        )

    async def record_embedding_cost(
        self,
        user_id: str,
        text: Union[str, List[str]],
        model: str = "text-embedding-3-small"
    ):
        """
        Record cost for embedding generation

        Args:
            user_id: User identifier
            text: Text or list of texts to embed
            model: Embedding model name
        """
        if not Config.ENABLE_COST_TRACKING:
            return

        # Count tokens
        if isinstance(text, list):
            total_tokens = sum(self.count_tokens(t, model) for t in text)
        else:
            total_tokens = self.count_tokens(text, model)

        # Calculate cost
        cost = self.COSTS.get(model, 0.0) * total_tokens

        # Record it
        self.user_costs[user_id] = self.user_costs.get(user_id, 0.0) + cost
        await self.save_user_costs(user_id)

        logger.debug(
            "embedding_cost_recorded",
            user_id=user_id,
            model=model,
            tokens=total_tokens,
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
        """
        Get total daily cost for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Total cost for the current day in dollars
        """
        await self.load_user_costs(user_id)
        return self.user_costs.get(user_id, 0.0)

    def estimate_completion_cost(
        self,
        messages: Union[str, List[Dict]],
        estimated_output_tokens: int,
        model: str
    ) -> float:
        """
        Estimate cost for a completion before making the API call

        Args:
            messages: Input messages
            estimated_output_tokens: Expected output length in tokens
            model: Model name

        Returns:
            Estimated cost in dollars
        """
        input_tokens = self.count_tokens(messages, model)
        return self.calculate_cost(input_tokens, estimated_output_tokens, model)

    def get_token_estimate(
        self,
        text: Union[str, List[Dict]],
        model: str = "gpt-4o"
    ) -> Dict[str, int]:
        """
        Get token count estimate for text

        Args:
            text: Text or messages to count
            model: Model name for encoding

        Returns:
            Dict with token count and character count
        """
        tokens = self.count_tokens(text, model)
        chars = len(text) if isinstance(text, str) else sum(
            len(str(m.get("content", ""))) for m in text if isinstance(m, dict)
        )

        return {
            "tokens": tokens,
            "characters": chars,
            "ratio": chars / tokens if tokens > 0 else 0
        }
    
    