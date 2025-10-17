"""
Custom Agent Creation Demo
Demonstrates how to create and configure custom agents with specialized capabilities
"""

import asyncio
import uuid
from datetime import datetime
from typing import List, Optional

from src.orchestration import (
    WorkerAgent,
    AgentRegistry,
    AgentPool,
    Task,
    AgentCapability,
    TaskPriority,
    TaskStatus,
    AgentStatus,
)
from src.services.cost_tracker import CostTracker

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


def create_custom_research_agent(
    agent_id: str,
    cost_tracker: CostTracker,
    openai_api_key: Optional[str] = None,
) -> WorkerAgent:
    """
    Create a custom research-focused agent with specialized instructions

    Args:
        agent_id: Unique identifier for the agent
        cost_tracker: Cost tracking instance
        openai_api_key: OpenAI API key (optional)

    Returns:
        Configured WorkerAgent instance
    """
    specialized_instructions = """
    As a research specialist, you should:
    - Prioritize academic and authoritative sources
    - Always verify facts from multiple sources
    - Include publication dates and author credentials when available
    - Organize findings in a structured, hierarchical format
    - Highlight areas of uncertainty or conflicting information
    """

    return WorkerAgent(
        agent_id=agent_id,
        name="Deep Research Specialist",
        capabilities=[AgentCapability.RESEARCH, AgentCapability.MEMORY],
        openai_api_key=openai_api_key,
        cost_tracker=cost_tracker,
        specialized_instructions=specialized_instructions,
    )


def create_custom_analyst_agent(
    agent_id: str,
    cost_tracker: CostTracker,
    openai_api_key: Optional[str] = None,
) -> WorkerAgent:
    """
    Create a custom analysis-focused agent

    Args:
        agent_id: Unique identifier for the agent
        cost_tracker: Cost tracking instance
        openai_api_key: OpenAI API key (optional)

    Returns:
        Configured WorkerAgent instance
    """
    specialized_instructions = """
    As a data analyst, you should:
    - Identify patterns, trends, and correlations in data
    - Use statistical reasoning when appropriate
    - Present findings with clear visualizations or structured summaries
    - Distinguish between correlation and causation
    - Provide confidence levels for your conclusions
    """

    return WorkerAgent(
        agent_id=agent_id,
        name="Data Analyst Pro",
        capabilities=[AgentCapability.ANALYSIS, AgentCapability.MEMORY],
        openai_api_key=openai_api_key,
        cost_tracker=cost_tracker,
        specialized_instructions=specialized_instructions,
    )


def create_custom_writer_agent(
    agent_id: str,
    cost_tracker: CostTracker,
    openai_api_key: Optional[str] = None,
) -> WorkerAgent:
    """
    Create a custom writing-focused agent

    Args:
        agent_id: Unique identifier for the agent
        cost_tracker: Cost tracking instance
        openai_api_key: OpenAI API key (optional)

    Returns:
        Configured WorkerAgent instance
    """
    specialized_instructions = """
    As a content writer, you should:
    - Write in a clear, engaging, and professional tone
    - Structure content with proper headings and paragraphs
    - Use transition words and logical flow
    - Include relevant examples and analogies
    - Tailor style to target audience (technical vs general)
    - Always cite sources properly
    """

    return WorkerAgent(
        agent_id=agent_id,
        name="Content Writer Plus",
        capabilities=[AgentCapability.WRITING, AgentCapability.MEMORY],
        openai_api_key=openai_api_key,
        cost_tracker=cost_tracker,
        specialized_instructions=specialized_instructions,
    )


def create_custom_generalist_agent(
    agent_id: str,
    cost_tracker: CostTracker,
    openai_api_key: Optional[str] = None,
) -> WorkerAgent:
    """
    Create a custom general-purpose agent with multiple capabilities

    Args:
        agent_id: Unique identifier for the agent
        cost_tracker: Cost tracking instance
        openai_api_key: OpenAI API key (optional)

    Returns:
        Configured WorkerAgent instance
    """
    specialized_instructions = """
    As a versatile generalist, you should:
    - Adapt your approach based on task requirements
    - Combine research, analysis, and writing skills as needed
    - Break complex tasks into logical steps
    - Leverage all available tools effectively
    - Deliver comprehensive, well-rounded results
    """

    return WorkerAgent(
        agent_id=agent_id,
        name="Versatile Generalist",
        capabilities=[
            AgentCapability.GENERAL,
            AgentCapability.RESEARCH,
            AgentCapability.ANALYSIS,
            AgentCapability.WRITING,
            AgentCapability.MEMORY,
        ],
        openai_api_key=openai_api_key,
        cost_tracker=cost_tracker,
        specialized_instructions=specialized_instructions,
    )


async def register_custom_agents(
    registry: AgentRegistry,
    cost_tracker: CostTracker,
    openai_api_key: Optional[str] = None,
) -> List[WorkerAgent]:
    """
    Create and register a suite of custom agents

    Args:
        registry: Agent registry instance
        cost_tracker: Cost tracking instance
        openai_api_key: OpenAI API key (optional)

    Returns:
        List of created agents
    """
    agents = []

    # Create custom agents
    research_agent = create_custom_research_agent(
        f"agent-research-{uuid.uuid4().hex[:8]}",
        cost_tracker,
        openai_api_key,
    )

    analyst_agent = create_custom_analyst_agent(
        f"agent-analyst-{uuid.uuid4().hex[:8]}",
        cost_tracker,
        openai_api_key,
    )

    writer_agent = create_custom_writer_agent(
        f"agent-writer-{uuid.uuid4().hex[:8]}",
        cost_tracker,
        openai_api_key,
    )

    generalist_agent = create_custom_generalist_agent(
        f"agent-generalist-{uuid.uuid4().hex[:8]}",
        cost_tracker,
        openai_api_key,
    )

    agents.extend([research_agent, analyst_agent, writer_agent, generalist_agent])

    # Initialize all agents with async context managers
    for agent in agents:
        await agent.__aenter__()

    # Register all agents
    for agent in agents:
        await registry.register_agent(
            agent_id=agent.agent_id,
            name=agent.name,
            capabilities=agent.capabilities,
        )

    return agents


async def demo_custom_agents():
    """
    Demonstration of creating and using custom agents
    """
    print("=" * 70)
    print("Custom Agent Creation Demo")
    print("=" * 70)

    # Initialize components
    cost_tracker = CostTracker()
    registry = AgentRegistry()

    print("\n1. Creating custom agents...")
    print("-" * 70)

    # Create custom agents
    agents = await register_custom_agents(registry, cost_tracker)

    for agent in agents:
        print(f"\n✓ Created: {agent.name}")
        print(f"  ID: {agent.agent_id}")
        print(f"  Capabilities: {', '.join(c.value for c in agent.capabilities)}")
        if agent.specialized_instructions:
            preview = agent.specialized_instructions.strip().split('\n')[1][:50]
            print(f"  Instructions: {preview}...")

    print("\n\n2. Demonstrating agent capabilities...")
    print("-" * 70)

    # Create test tasks for each agent type
    tasks = [
        Task(
            task_id=f"task-{uuid.uuid4().hex[:8]}",
            description="Research the latest breakthroughs in renewable energy storage",
            required_capabilities=[AgentCapability.RESEARCH],
            priority=TaskPriority.HIGH,
            created_at=datetime.utcnow(),
            status=TaskStatus.PENDING,
            user_id="demo_user",
        ),
        Task(
            task_id=f"task-{uuid.uuid4().hex[:8]}",
            description="Analyze trends in electric vehicle adoption over the past 5 years",
            required_capabilities=[AgentCapability.ANALYSIS],
            priority=TaskPriority.NORMAL,
            created_at=datetime.utcnow(),
            status=TaskStatus.PENDING,
            user_id="demo_user",
        ),
        Task(
            task_id=f"task-{uuid.uuid4().hex[:8]}",
            description="Write a compelling summary of climate tech innovations",
            required_capabilities=[AgentCapability.WRITING],
            priority=TaskPriority.NORMAL,
            created_at=datetime.utcnow(),
            status=TaskStatus.PENDING,
            user_id="demo_user",
        ),
    ]

    # Execute tasks with custom agents
    for task in tasks:
        # Find matching agent
        matching_agent = None
        for agent in agents:
            if await agent.can_execute_task(task):
                matching_agent = agent
                break

        if not matching_agent:
            print(f"\n✗ No agent found for task: {task.description}")
            continue

        print(f"\n→ Assigning task to {matching_agent.name}...")
        print(f"  Task: {task.description}")

        # Update registry
        await registry.update_status(
            matching_agent.agent_id, AgentStatus.BUSY, task.task_id
        )

        # Execute task
        result = await matching_agent.execute_task(task)

        # Update registry
        await registry.record_task_completion(
            matching_agent.agent_id,
            success=result.success,
            cost=result.cost,
        )
        await registry.update_status(matching_agent.agent_id, AgentStatus.IDLE)

        if result.success:
            print(f"  ✓ Completed in {result.duration_seconds:.2f}s")
            print(f"  Cost: ${result.cost:.4f}")
            print(f"\n  Preview: {result.result[:150]}...")
            if result.citations:
                print(f"  Citations: {len(result.citations)} sources")
        else:
            print(f"  ✗ Failed: {result.error}")

    print("\n\n3. Agent Registry Summary...")
    print("-" * 70)

    # Display registry statistics
    for agent in agents:
        metadata = await registry.get_agent(agent.agent_id)
        if metadata:
            print(f"\n{metadata.name}:")
            print(f"  Status: {metadata.status.value}")
            print(f"  Tasks completed: {metadata.tasks_completed}")
            print(f"  Tasks failed: {metadata.tasks_failed}")
            print(f"  Total cost: ${metadata.total_cost:.4f}")

    print("\n" + "=" * 70)
    print("Demo completed!")
    print("=" * 70)

    # Cleanup: properly exit all agents
    for agent in agents:
        await agent.__aexit__(None, None, None)


async def demo_agent_pool_with_custom_agents():
    """
    Demonstration of using custom agents with AgentPool
    """
    print("\n\n" + "=" * 70)
    print("Custom Agents with AgentPool Demo")
    print("=" * 70)

    cost_tracker = CostTracker()
    registry = AgentRegistry()

    async with AgentPool(registry, cost_tracker, max_agents=4) as pool:
        # Register custom agents
        agents = await register_custom_agents(registry, cost_tracker)

        # Add agents to pool
        for agent in agents:
            pool.agents[agent.agent_id] = agent

        print(f"\n✓ Pool initialized with {len(agents)} custom agents")

        # Create diverse tasks
        tasks = [
            Task(
                task_id=f"task-{uuid.uuid4().hex[:8]}",
                description="Find information about AI safety research initiatives",
                required_capabilities=[AgentCapability.RESEARCH],
                priority=TaskPriority.HIGH,
                created_at=datetime.utcnow(),
                status=TaskStatus.PENDING,
                user_id="pool_user",
            ),
            Task(
                task_id=f"task-{uuid.uuid4().hex[:8]}",
                description="Compare different approaches to AI alignment",
                required_capabilities=[AgentCapability.ANALYSIS],
                priority=TaskPriority.NORMAL,
                created_at=datetime.utcnow(),
                status=TaskStatus.PENDING,
                user_id="pool_user",
            ),
        ]

        # Execute in parallel
        async def execute_task(task: Task):
            agent = await pool.get_available_agent(task.required_capabilities)
            if agent:
                await registry.update_status(agent.agent_id, AgentStatus.BUSY, task.task_id)
                result = await agent.execute_task(task)
                await registry.record_task_completion(agent.agent_id, result.success, result.cost)
                await registry.update_status(agent.agent_id, AgentStatus.IDLE)
                return result
            return None

        results = await asyncio.gather(*[execute_task(task) for task in tasks])

        # Summary
        successful = sum(1 for r in results if r and r.success)
        total_cost = sum(r.cost for r in results if r)

        print(f"\n✓ Completed {successful}/{len(tasks)} tasks")
        print(f"✓ Total cost: ${total_cost:.4f}")

        # Cleanup: properly exit all agents
        for agent in agents:
            await agent.__aexit__(None, None, None)

    print("\n" + "=" * 70)


if __name__ == "__main__":
    # Run both demos
    asyncio.run(demo_custom_agents())
    asyncio.run(demo_agent_pool_with_custom_agents())
