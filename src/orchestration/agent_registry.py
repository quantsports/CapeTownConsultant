"""
Agent registry
Tracks all active agents and their states
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Set
from collections import defaultdict

from src.core.logging import logger
from src.orchestration.models import AgentMetadata, AgentStatus, AgentCapability


class AgentRegistry:
    """
    Central registry for tracking all active agents
    Thread-safe for concurrent access
    """

    def __init__(self):
        self._agents: Dict[str, AgentMetadata] = {}
        self._capability_index: Dict[AgentCapability, Set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def register_agent(
        self, agent_id: str, name: str, capabilities: List[AgentCapability]
    ) -> AgentMetadata:
        """
        Register a new agent

        Args:
            agent_id: Unique identifier for agent
            name: Human-readable name
            capabilities: List of agent capabilities

        Returns:
            AgentMetadata object
        """
        async with self._lock:
            if agent_id in self._agents:
                logger.warning("agent_already_registered", agent_id=agent_id)
                return self._agents[agent_id]

            metadata = AgentMetadata(
                agent_id=agent_id,
                name=name,
                capabilities=capabilities,
                status=AgentStatus.INITIALIZING,
                created_at=datetime.utcnow(),
                last_active=datetime.utcnow(),
            )

            self._agents[agent_id] = metadata

            # Index by capabilities
            for capability in capabilities:
                self._capability_index[capability].add(agent_id)

            logger.info(
                "agent_registered",
                agent_id=agent_id,
                name=name,
                capabilities=[c.value for c in capabilities],
            )

            return metadata

    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent

        Args:
            agent_id: Agent to unregister

        Returns:
            True if agent was unregistered, False if not found
        """
        async with self._lock:
            if agent_id not in self._agents:
                return False

            metadata = self._agents[agent_id]

            # Remove from capability index
            for capability in metadata.capabilities:
                self._capability_index[capability].discard(agent_id)

            del self._agents[agent_id]

            logger.info("agent_unregistered", agent_id=agent_id)
            return True

    async def update_status(
        self, agent_id: str, status: AgentStatus, current_task_id: Optional[str] = None
    ) -> bool:
        """
        Update agent status

        Args:
            agent_id: Agent to update
            status: New status
            current_task_id: Current task (if any)

        Returns:
            True if updated, False if agent not found
        """
        async with self._lock:
            if agent_id not in self._agents:
                return False

            self._agents[agent_id].status = status
            self._agents[agent_id].last_active = datetime.utcnow()

            if current_task_id is not None:
                self._agents[agent_id].current_task_id = current_task_id

            logger.debug(
                "agent_status_updated",
                agent_id=agent_id,
                status=status.value,
                task_id=current_task_id,
            )

            return True

    async def record_task_completion(
        self, agent_id: str, success: bool, cost: float = 0.0
    ) -> bool:
        """
        Record task completion metrics

        Args:
            agent_id: Agent that completed task
            success: Whether task succeeded
            cost: Cost incurred

        Returns:
            True if recorded, False if agent not found
        """
        async with self._lock:
            if agent_id not in self._agents:
                return False

            metadata = self._agents[agent_id]

            if success:
                metadata.tasks_completed += 1
            else:
                metadata.tasks_failed += 1

            metadata.total_cost += cost
            metadata.last_active = datetime.utcnow()
            metadata.current_task_id = None

            return True

    async def get_agent(self, agent_id: str) -> Optional[AgentMetadata]:
        """
        Get agent metadata

        Args:
            agent_id: Agent to retrieve

        Returns:
            AgentMetadata if found, None otherwise
        """
        async with self._lock:
            return self._agents.get(agent_id)

    async def get_agents_by_capability(
        self, capability: AgentCapability, status_filter: Optional[AgentStatus] = None
    ) -> List[AgentMetadata]:
        """
        Get all agents with a specific capability

        Args:
            capability: Required capability
            status_filter: Optional status filter (e.g., only IDLE agents)

        Returns:
            List of matching agents
        """
        async with self._lock:
            agent_ids = self._capability_index.get(capability, set())
            agents = [self._agents[aid] for aid in agent_ids if aid in self._agents]

            if status_filter:
                agents = [a for a in agents if a.status == status_filter]

            return agents

    async def get_available_agent(
        self, required_capabilities: List[AgentCapability]
    ) -> Optional[AgentMetadata]:
        """
        Find an available (IDLE) agent with required capabilities

        Args:
            required_capabilities: List of required capabilities

        Returns:
            AgentMetadata of available agent, or None if none found
        """
        async with self._lock:
            # Find agents that have ALL required capabilities
            candidate_ids = None

            for capability in required_capabilities:
                capable_ids = self._capability_index.get(capability, set())
                if candidate_ids is None:
                    candidate_ids = capable_ids.copy()
                else:
                    candidate_ids &= capable_ids

            if not candidate_ids:
                return None

            # Find first IDLE agent
            for agent_id in candidate_ids:
                agent = self._agents.get(agent_id)
                if agent and agent.status == AgentStatus.IDLE:
                    return agent

            return None

    async def get_all_agents(
        self, status_filter: Optional[AgentStatus] = None
    ) -> List[AgentMetadata]:
        """
        Get all registered agents

        Args:
            status_filter: Optional status filter

        Returns:
            List of all agents (optionally filtered)
        """
        async with self._lock:
            agents = list(self._agents.values())

            if status_filter:
                agents = [a for a in agents if a.status == status_filter]

            return agents

    async def get_statistics(self) -> Dict:
        """
        Get registry statistics

        Returns:
            Dictionary with stats
        """
        async with self._lock:
            status_counts = defaultdict(int)
            total_tasks = 0
            total_failures = 0
            total_cost = 0.0

            for agent in self._agents.values():
                status_counts[agent.status.value] += 1
                total_tasks += agent.tasks_completed
                total_failures += agent.tasks_failed
                total_cost += agent.total_cost

            return {
                "total_agents": len(self._agents),
                "status_counts": dict(status_counts),
                "total_tasks_completed": total_tasks,
                "total_tasks_failed": total_failures,
                "total_cost": total_cost,
                "capabilities": {
                    cap.value: len(ids) for cap, ids in self._capability_index.items()
                },
            }

    async def clear(self):
        """Clear all agents (for testing/shutdown)"""
        async with self._lock:
            self._agents.clear()
            self._capability_index.clear()
            logger.info("agent_registry_cleared")
