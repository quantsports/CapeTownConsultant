"""
Assistant interface with Phase 2 enhancements
- Streaming support
- Progress callbacks
- Smart caching integration
"""
import asyncio
import re
from typing import Dict, Optional, AsyncIterator

from src.agent.autonomous import AutonomousAgent
from src.services.cost_tracker import CostTracker


class AutonomousAssistant:
    """Enhanced assistant interface with streaming and caching"""

    def __init__(
        self,
        cost_tracker: Optional[CostTracker] = None,
        enable_streaming: bool = False
    ):
        self.cost_tracker = cost_tracker or CostTracker()
        self.agent: Optional[AutonomousAgent] = None
        self.enable_streaming = enable_streaming

    async def __aenter__(self):
        """Initialize agent"""
        self.agent = await AutonomousAgent(
            cost_tracker=self.cost_tracker
        ).__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup agent"""
        if self.agent:
            await self.agent.__aexit__(exc_type, exc_val, exc_tb)

    async def chat(self, message: str, user_id: str = "default") -> str:
        """
        Send a message and get complete response

        Uses concurrent tool execution for faster responses
        """
        if not self.agent:
            raise RuntimeError("Assistant not initialized. Use 'async with' context manager.")
        return await self.agent.chat(message, user_id)

    async def chat_stream(
        self,
        message: str,
        user_id: str = "default"
    ) -> AsyncIterator[str]:
        """
        Send a message and stream response chunks

        Yields:
            Progress updates and response chunks

        Example:
            async for chunk in assistant.chat_stream("Hello"):
                print(chunk, end='', flush=True)
        """
        if not self.agent:
            raise RuntimeError("Assistant not initialized. Use 'async with' context manager.")

        async for chunk in self.agent.chat_stream(message, user_id):
            yield chunk

    def set_progress_callback(self, callback):
        """
        Set callback for progress updates

        Callback will receive progress messages during execution
        Useful for UI progress bars
        """
        if self.agent:
            self.agent.set_progress_callback(callback)

    def clear_history(self):
        """Clear conversation history"""
        if self.agent:
            self.agent.clear_history()

    async def get_costs(self, user_id: str = "default") -> Dict[str, float]:
        """Get cost summary for user"""
        return await self.cost_tracker.get_user_costs(user_id)