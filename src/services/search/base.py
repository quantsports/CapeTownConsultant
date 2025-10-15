"""
Base search engine interface
"""

from abc import ABC, abstractmethod
from typing import Optional
import httpx

from src.core.models import ToolResult
from src.services.cost_tracker import CostTracker
from src.config.settings import Config


class BaseSearchEngine(ABC):
    """Base class for search engines"""

    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        self.cost_tracker = cost_tracker
        self.http_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Initialize HTTP client"""
        self.http_client = httpx.AsyncClient(
            timeout=Config.TIMEOUT_SECONDS,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
            http2=True
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup HTTP client"""
        if self.http_client:
            await self.http_client.aclose()

    @abstractmethod
    async def search(self, query: str, user_id: str = "default", **kwargs) -> ToolResult:
        """Execute search"""
        pass