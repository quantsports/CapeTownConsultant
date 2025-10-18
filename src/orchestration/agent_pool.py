"""
Agent pool manager
Manages lifecycle of worker agents
FIXES: High #5 - Resource leak in cleanup (errors ignored)
FIXES: Medium #9 - Poor error context in worker failures
"""

import asyncio
import uuid
import traceback
from typing import Dict, List, Optional

from src.core.logging import logger
from src.services.cost_tracker import CostTracker
from src.orchestration.models import AgentCapability, AgentStatus, AgentMetadata
from src.orchestration.worker_agent import WorkerAgent
from src.orchestration.agent_registry import AgentRegistry


class AgentPool:
    """
    Manages a pool of worker agents
    Handles spawning, initialization, and cleanup
    """

    def __init__(
        self,
        registry: AgentRegistry,
        cost_tracker: Optional[CostTracker] = None,
        max_agents: int = 10,
    ):
        """
        Initialize agent pool

        Args:
            registry: Agent registry for tracking
            cost_tracker: Shared cost tracker
            max_agents: Maximum number of concurrent agents
        """
        self.registry = registry
        self.cost_tracker = cost_tracker or CostTracker()
        self.max_agents = max_agents
        self._agents: Dict[str, WorkerAgent] = {}
        self._lock = asyncio.Lock()

        logger.info("agent_pool_initialized", max_agents=max_agents)

    async def register_existing_agent(self, agent: WorkerAgent) -> None:
        """
        Register an already-initialized agent with the pool

        Args:
            agent: Initialized WorkerAgent to register

        Raises:
            RuntimeError: If max agents limit reached
        """
        async with self._lock:
            if len(self._agents) >= self.max_agents:
                raise RuntimeError(
                    f"Cannot register agent: max limit ({self.max_agents}) reached"
                )

            # Store in pool
            self._agents[agent.agent_id] = agent

            logger.info(
                "existing_agent_registered",
                agent_id=agent.agent_id,
                name=agent.name,
            )

    async def spawn_agent(
        self,
        name: str,
        capabilities: List[AgentCapability],
        specialized_instructions: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> WorkerAgent:
        """
        Spawn a new worker agent

        Args:
            name: Agent name
            capabilities: List of capabilities
            specialized_instructions: Optional specialized instructions
            agent_id: Optional custom agent ID (generated if not provided)

        Returns:
            Initialized WorkerAgent

        Raises:
            RuntimeError: If max agents limit reached
        """
        async with self._lock:
            if len(self._agents) >= self.max_agents:
                raise RuntimeError(
                    f"Cannot spawn agent: max limit ({self.max_agents}) reached"
                )

            # Generate agent ID if not provided
            if agent_id is None:
                agent_id = f"agent-{uuid.uuid4().hex[:8]}"

            # Register in registry
            await self.registry.register_agent(
                agent_id=agent_id,
                name=name,
                capabilities=capabilities,
                status=AgentStatus.INITIALIZING,
            )

            # Create agent
            agent = WorkerAgent(
                agent_id=agent_id,
                name=name,
                capabilities=capabilities,
                specialized_instructions=specialized_instructions,
                cost_tracker=self.cost_tracker,
            )

            # Initialize agent
            try:
                await agent.__aenter__()

                # Update status to active
                await self.registry.update_status(agent_id, AgentStatus.ACTIVE)

                # Add to pool
                self._agents[agent_id] = agent

                logger.info(
                    "agent_spawned",
                    agent_id=agent_id,
                    name=name,
                    capabilities=[c.value for c in capabilities],
                )

                return agent

            except Exception as e:
                # MEDIUM FIX #9: Include traceback in error logs
                logger.error(
                    "agent_spawn_failed",
                    agent_id=agent_id,
                    name=name,
                    error=str(e),
                    traceback=traceback.format_exc()
                )

                # Clean up failed registration
                await self.registry.unregister_agent(agent_id)
                raise

    async def spawn_specialized_agents(
        self, count: int = 3
    ) -> Dict[str, WorkerAgent]:
        """
        Spawn a set of specialized agents

        Args:
            count: Number of specialized agents to spawn (1-3)

        Returns:
            Dictionary mapping agent_id to WorkerAgent
        """
        agents = {}

        if count < 1:
            count = 1
        if count > 3:
            count = 3

        # Research specialist
        research_agent = await self.spawn_agent(
            name="Research Specialist",
            capabilities=[
                AgentCapability.SEARCH,
                AgentCapability.MEMORY,
                AgentCapability.GENERAL,
            ],
            specialized_instructions="""You excel at finding and synthesizing information. 
Focus on accuracy, credibility, and comprehensive research.""",
        )
        agents[research_agent.agent_id] = research_agent

        if count >= 2:
            # Analysis specialist
            analysis_agent = await self.spawn_agent(
                name="Analysis Specialist",
                capabilities=[
                    AgentCapability.ANALYSIS,
                    AgentCapability.MEMORY,
                    AgentCapability.GENERAL,
                ],
                specialized_instructions="""You excel at critical thinking and analysis. 
Focus on drawing insights and making connections.""",
            )
            agents[analysis_agent.agent_id] = analysis_agent

        if count >= 3:
            # Writing specialist
            writing_agent = await self.spawn_agent(
                name="Writing Specialist",
                capabilities=[
                    AgentCapability.WRITING,
                    AgentCapability.MEMORY,
                    AgentCapability.GENERAL,
                ],
                specialized_instructions="""You excel at creating clear, well-structured content. 
Focus on clarity, organization, and engaging prose.""",
            )
            agents[writing_agent.agent_id] = writing_agent

        logger.info("specialized_agents_spawned", count=len(agents))
        return agents

    async def get_agent(self, agent_id: str) -> Optional[WorkerAgent]:
        """
        Get agent by ID

        Args:
            agent_id: Agent identifier

        Returns:
            WorkerAgent if found, None otherwise
        """
        async with self._lock:
            return self._agents.get(agent_id)

    async def remove_agent(self, agent_id: str) -> bool:
        """
        Remove and cleanup an agent

        Args:
            agent_id: Agent to remove

        Returns:
            True if removed, False if not found
        """
        async with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return False

            # Cleanup agent resources
            try:
                await agent.__aexit__(None, None, None)
            except Exception as e:
                # MEDIUM FIX #9: Include traceback in cleanup errors
                logger.error(
                    "agent_cleanup_error",
                    agent_id=agent_id,
                    error=str(e),
                    traceback=traceback.format_exc()
                )

            # Remove from pool
            del self._agents[agent_id]

            # Unregister from registry
            await self.registry.unregister_agent(agent_id)

            logger.info("agent_removed", agent_id=agent_id)
            return True

    async def get_all_agents(self) -> List[WorkerAgent]:
        """
        Get all agents in pool

        Returns:
            List of all agents
        """
        async with self._lock:
            return list(self._agents.values())

    async def get_available_agent(
        self, required_capabilities: List[AgentCapability]
    ) -> Optional[WorkerAgent]:
        """
        Find an available agent with required capabilities

        Args:
            required_capabilities: Required capabilities

        Returns:
            Available WorkerAgent or None
        """
        # Query registry for available agent
        metadata = await self.registry.get_available_agent(required_capabilities)

        if not metadata:
            return None

        async with self._lock:
            return self._agents.get(metadata.agent_id)

    async def get_pool_statistics(self) -> Dict:
        """
        Get pool statistics

        Returns:
            Dictionary with pool stats
        """
        registry_stats = await self.registry.get_statistics()

        async with self._lock:
            return {
                "total_agents": len(self._agents),
                "max_agents": self.max_agents,
                "utilization": (
                    len(self._agents) / self.max_agents if self.max_agents > 0 else 0
                ),
                **registry_stats,
            }

    async def shutdown(self):
        """
        Shutdown pool and cleanup all agents
        HIGH FIX #5: Collect all cleanup errors and raise after shutdown completes
        """
        async with self._lock:
            logger.info("agent_pool_shutting_down", agent_count=len(self._agents))

            # HIGH FIX #5: Collect all errors during cleanup
            cleanup_errors = []

            # Cleanup all agents
            for agent_id, agent in list(self._agents.items()):
                try:
                    await agent.__aexit__(None, None, None)
                    await self.registry.unregister_agent(agent_id)
                except Exception as e:
                    # MEDIUM FIX #9: Include full traceback
                    error_info = {
                        "agent_id": agent_id,
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    }
                    cleanup_errors.append(error_info)
                    logger.error(
                        "agent_shutdown_error",
                        **error_info
                    )

            self._agents.clear()
            logger.info("agent_pool_shutdown_complete")

            # HIGH FIX #5: Raise collected errors if any occurred
            if cleanup_errors:
                error_summary = "\n".join(
                    f"Agent {e['agent_id']}: {e['error']}"
                    for e in cleanup_errors
                )
                raise RuntimeError(
                    f"Errors during agent pool shutdown ({len(cleanup_errors)} agents):\n{error_summary}"
                )

    async def __aenter__(self):
        """Context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.shutdown()