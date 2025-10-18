"""
Assistant interface with orchestration support
Fixed to properly integrate multi-agent orchestration
"""
import asyncio
import re
from typing import Dict, Optional, AsyncIterator

from src.agent.autonomous import AutonomousAgent
from src.services.cost_tracker import CostTracker


class AutonomousAssistant:
    """Enhanced assistant interface with orchestration support"""

    def __init__(
        self,
        cost_tracker: Optional[CostTracker] = None,
        enable_streaming: bool = False,
        enable_orchestration: bool = True,
        api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ) -> None:
        """
        Initialize assistant

        Args:
            cost_tracker: Cost tracking instance
            enable_streaming: Enable streaming responses
            enable_orchestration: Enable multi-agent orchestration (default: True)
            api_key: Optional API key for LLM provider (alias for openai_api_key)
            openai_api_key: Optional explicit OpenAI API key
        """
        self.cost_tracker = cost_tracker or CostTracker()
        self.agent: Optional[AutonomousAgent] = None
        self.enable_streaming = enable_streaming
        self.enable_orchestration = enable_orchestration
        # Prefer explicit api_key if provided, else fall back to openai_api_key
        self.openai_api_key: Optional[str] = api_key if api_key is not None else openai_api_key

    async def __aenter__(self):
        """Initialize agent with orchestration support"""
        self.agent = await AutonomousAgent(
            cost_tracker=self.cost_tracker,
            enable_orchestration=self.enable_orchestration
        ).__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup agent"""
        if self.agent:
            await self.agent.__aexit__(exc_type, exc_val, exc_tb)

    async def chat(self, message: str, user_id: str = "default") -> str:
        """
        Send a message and get complete response
        Uses orchestration for complex queries, traditional mode for simple ones
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
        """
        if not self.agent:
            raise RuntimeError("Assistant not initialized. Use 'async with' context manager.")

        async for chunk in self.agent.chat_stream(message, user_id):
            yield chunk

    def set_progress_callback(self, callback):
        """
        Set callback for progress updates
        Callback will receive progress messages during execution
        """
        if self.agent:
            self.agent.set_progress_callback(callback)

    def toggle_orchestration(self, enabled: bool):
        """
        Toggle orchestration mode at runtime

        Args:
            enabled: True to enable orchestration, False for traditional mode
        """
        if self.agent:
            self.agent.enable_orchestration = enabled
            status = "enabled" if enabled else "disabled"
            print(f"🎭 Orchestration {status}")
        else:
            raise RuntimeError("Assistant not initialized")

    def get_orchestration_status(self) -> bool:
        """Check if orchestration is currently enabled"""
        return self.agent.enable_orchestration if self.agent else self.enable_orchestration

    def clear_history(self):
        """Clear conversation history"""
        if self.agent:
            self.agent.clear_history()

    async def get_costs(self, user_id: str = "default") -> Dict[str, float]:
        """Get cost summary for user"""
        return await self.cost_tracker.get_user_costs(user_id)