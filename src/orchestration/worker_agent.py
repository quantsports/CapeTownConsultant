"""
Worker agent
Specialized agent for task execution in multi-agent system
"""

import time
from typing import List, Optional
from datetime import datetime

from src.agent.autonomous import AutonomousAgent
from src.core.logging import logger
from src.orchestration.models import Task, WorkResult, AgentCapability, TaskStatus


class WorkerAgent(AutonomousAgent):
    """
    Worker agent that extends AutonomousAgent with task execution capabilities
    Designed to work within a multi-agent orchestration system
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        capabilities: List[AgentCapability],
        openai_api_key: Optional[str] = None,
        cost_tracker=None,
        specialized_instructions: Optional[str] = None,
    ):
        """
        Initialize worker agent

        Args:
            agent_id: Unique identifier for this agent
            name: Human-readable name
            capabilities: List of agent capabilities
            openai_api_key: OpenAI API key
            cost_tracker: Shared cost tracker
            specialized_instructions: Additional system instructions
        """
        super().__init__(openai_api_key=openai_api_key, cost_tracker=cost_tracker)

        self.agent_id = agent_id
        self.name = name
        self.capabilities = capabilities
        self.specialized_instructions = specialized_instructions
        self.current_task: Optional[Task] = None

        logger.info(
            "worker_agent_initialized",
            agent_id=agent_id,
            name=name,
            capabilities=[c.value for c in capabilities],
        )

    def _get_system_message(self, task: Task) -> str:
        """
        Generate system message based on agent capabilities and task

        Args:
            task: Task to execute

        Returns:
            System message string
        """
        base_instructions = f"""You are {self.name} (Agent ID: {self.agent_id}), a specialized knowledge worker.

YOUR CAPABILITIES:
{chr(10).join(f"- {cap.value.upper()}: {self._get_capability_description(cap)}" for cap in self.capabilities)}

CURRENT TASK:
{task.description}

TASK REQUIREMENTS:
{', '.join(cap.value for cap in task.required_capabilities)}

INSTRUCTIONS:
1. Execute the task using your available tools
2. Be thorough and cite all sources
3. If you need information, use search tools
4. Store important findings in memory
5. Provide a complete, well-structured answer

Remember: You are part of a larger research team. Focus on delivering high-quality results for this specific task."""

        if self.specialized_instructions:
            base_instructions += (
                f"\n\nSPECIALIZED INSTRUCTIONS:\n{self.specialized_instructions}"
            )

        return base_instructions

    def _get_capability_description(self, capability: AgentCapability) -> str:
        """Get human-readable description of capability"""
        descriptions = {
            AgentCapability.RESEARCH: "Web search, information gathering, fact-finding",
            AgentCapability.ANALYSIS: "Data analysis, synthesis, pattern recognition",
            AgentCapability.WRITING: "Content generation, summarization, documentation",
            AgentCapability.MEMORY: "Knowledge storage and retrieval",
            AgentCapability.COORDINATION: "Multi-agent task coordination",
            AgentCapability.GENERAL: "General-purpose task execution",
        }
        return descriptions.get(capability, "Unknown capability")

    async def execute_task(self, task: Task) -> WorkResult:
        """
        Execute a task and return results

        Args:
            task: Task to execute

        Returns:
            WorkResult with execution outcome
        """
        start_time = time.time()
        self.current_task = task

        logger.info(
            "task_execution_started",
            agent_id=self.agent_id,
            task_id=task.task_id,
            description=task.description[:100],
        )

        try:
            # Update conversation history with specialized system message
            system_message = self._get_system_message(task)
            self.conversation_history = [{"role": "system", "content": system_message}]

            # Execute the task using parent class chat method
            initial_cost = await self.cost_tracker.get_daily_total(task.user_id)

            response = await self.chat(
                user_message=task.description, user_id=task.user_id
            )

            final_cost = await self.cost_tracker.get_daily_total(task.user_id)
            task_cost = final_cost - initial_cost

            # Collect citations
            citations = self.citation_manager.citations

            duration = time.time() - start_time

            result = WorkResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                result=response,
                cost=task_cost,
                duration_seconds=duration,
                citations=citations,
                metadata={
                    "agent_name": self.name,
                    "capabilities_used": [c.value for c in self.capabilities],
                    "started_at": datetime.utcnow().isoformat(),
                },
            )

            logger.info(
                "task_execution_completed",
                agent_id=self.agent_id,
                task_id=task.task_id,
                duration=f"{duration:.2f}s",
                cost=f"${task_cost:.4f}",
            )

            return result

        except Exception as e:
            duration = time.time() - start_time

            logger.error(
                "task_execution_failed",
                agent_id=self.agent_id,
                task_id=task.task_id,
                error=str(e),
            )

            return WorkResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                result=None,
                error=str(e),
                duration_seconds=duration,
            )

        finally:
            self.current_task = None
            # Clear conversation history for next task
            self.conversation_history = []
            self.citation_manager.clear()

    async def can_execute_task(self, task: Task) -> bool:
        """
        Check if this agent can execute the given task

        Args:
            task: Task to check

        Returns:
            True if agent has required capabilities
        """
        return all(cap in self.capabilities for cap in task.required_capabilities)

    def get_info(self) -> dict:
        """
        Get agent information

        Returns:
            Dictionary with agent details
        """
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "capabilities": [c.value for c in self.capabilities],
            "current_task_id": self.current_task.task_id if self.current_task else None,
            "has_specialized_instructions": bool(self.specialized_instructions),
        }
