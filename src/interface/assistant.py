"""
Assistant interface
Main user-facing interface
"""

from typing import Dict, Optional

from src.agent.autonomous import AutonomousAgent
from src.services.cost_tracker import CostTracker


class AutonomousAssistant:
    """Main assistant interface"""

    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        self.cost_tracker = cost_tracker or CostTracker()
        self.agent: Optional[AutonomousAgent] = None

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
        """Send a message and get response"""
        if not self.agent:
            raise RuntimeError("Assistant not initialized. Use 'async with' context manager.")
        return await self.agent.chat(message, user_id)

    def clear_history(self):
        """Clear conversation history"""
        if self.agent:
            self.agent.clear_history()

    async def get_costs(self, user_id: str = "default") -> Dict[str, float]:
        """Get cost summary for user"""
        return await self.cost_tracker.get_user_costs(user_id)