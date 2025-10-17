"""
Basic multi-agent orchestration example
Demonstrates spawning agents and executing tasks
"""

import asyncio
import uuid
from datetime import datetime

from src.orchestration import (
    AgentRegistry,
    AgentPool,
    Task,
    AgentCapability,
    TaskPriority,
    TaskStatus,
)
from src.services.cost_tracker import CostTracker

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
async def main():
    """
    Example: Spawn multiple agents and execute parallel tasks
    """

    print("=" * 60)
    print("Multi-Agent System - Basic Example")
    print("=" * 60)

    # Initialize components
    cost_tracker = CostTracker()
    registry = AgentRegistry()

    async with AgentPool(registry, cost_tracker, max_agents=5) as pool:

        # Spawn specialized agents
        print("\n1. Spawning specialized agents...")
        agents = await pool.spawn_specialized_agents()

        print(f"   ✓ Spawned {len(agents)} agents:")
        for agent_id, agent in agents.items():
            print(f"     - {agent.name} ({agent_id})")

        # Create tasks
        print("\n2. Creating tasks...")
        tasks = [
            Task(
                task_id=f"task-{uuid.uuid4().hex[:8]}",
                description="Research the latest developments in quantum computing",
                required_capabilities=[AgentCapability.RESEARCH],
                priority=TaskPriority.HIGH,
                created_at=datetime.utcnow(),
                status=TaskStatus.PENDING,
                user_id="example_user",
            ),
            Task(
                task_id=f"task-{uuid.uuid4().hex[:8]}",
                description="Analyze the key trends in artificial intelligence from the research",
                required_capabilities=[AgentCapability.ANALYSIS],
                priority=TaskPriority.NORMAL,
                created_at=datetime.utcnow(),
                status=TaskStatus.PENDING,
                user_id="example_user",
            ),
            Task(
                task_id=f"task-{uuid.uuid4().hex[:8]}",
                description="Write a brief summary of quantum computing developments",
                required_capabilities=[AgentCapability.WRITING],
                priority=TaskPriority.NORMAL,
                created_at=datetime.utcnow(),
                status=TaskStatus.PENDING,
                user_id="example_user",
            ),
        ]

        print(f"   ✓ Created {len(tasks)} tasks")
        for task in tasks:
            print(f"     - {task.description[:60]}...")

        # Execute tasks in parallel
        print("\n3. Executing tasks in parallel...")

        async def execute_task(task: Task):
            """Helper to execute a single task"""
            # Find available agent
            agent = await pool.get_available_agent(task.required_capabilities)

            if not agent:
                print(f"   ✗ No available agent for task {task.task_id}")
                return None

            # Update registry
            from src.orchestration.models import AgentStatus

            await registry.update_status(agent.agent_id, AgentStatus.BUSY, task.task_id)

            print(f"   → {agent.name} executing: {task.description[:50]}...")

            # Execute task
            result = await agent.execute_task(task)

            # Update registry
            await registry.record_task_completion(
                agent.agent_id, success=result.success, cost=result.cost
            )
            await registry.update_status(agent.agent_id, AgentStatus.IDLE)

            if result.success:
                print(
                    f"   ✓ {agent.name} completed task in {result.duration_seconds:.2f}s"
                )
            else:
                print(f"   ✗ {agent.name} failed: {result.error}")

            return result

        # Execute all tasks concurrently
        results = await asyncio.gather(*[execute_task(task) for task in tasks])

        # Display results
        print("\n4. Results:")
        print("-" * 60)
        for i, result in enumerate(results):
            if result and result.success:
                print(f"\nTask {i+1} ({result.task_id}):")
                print(f"Agent: {result.agent_id}")
                print(f"Duration: {result.duration_seconds:.2f}s")
                print(f"Cost: ${result.cost:.4f}")
                print(f"\nResult:\n{result.result[:200]}...")
                if result.citations:
                    print(f"\nCitations: {len(result.citations)} sources")

        # Display statistics
        print("\n5. Pool Statistics:")
        print("-" * 60)
        stats = await pool.get_pool_statistics()
        print(f"Total agents: {stats['total_agents']}")
        print(f"Tasks completed: {stats['total_tasks_completed']}")
        print(f"Tasks failed: {stats['total_tasks_failed']}")
        print(f"Total cost: ${stats['total_cost']:.4f}")
        print(f"Status breakdown: {stats['status_counts']}")

    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
