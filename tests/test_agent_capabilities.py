"""
Test Scratchpad for Agent Capabilities
Comprehensive testing of multi-agent orchestration system
"""

import asyncio
from typing import List

from src.orchestration.models import (
    AgentCapability,
    TaskPriority,
    Task,
    AgentStatus,
)
from src.orchestration.agent_registry import AgentRegistry
from src.orchestration.agent_pool import AgentPool
from src.orchestration.worker_agent import WorkerAgent
from src.services.cost_tracker import CostTracker
from src.core.logging import logger
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
# =============================================================================
# Test Configuration
# =============================================================================

TEST_USER_ID = "test_user_001"

# Available capabilities to test
ALL_CAPABILITIES = [
    AgentCapability.RESEARCH,
    AgentCapability.ANALYSIS,
    AgentCapability.WRITING,
    AgentCapability.MEMORY,
    AgentCapability.COORDINATION,
    AgentCapability.GENERAL,
    AgentCapability.SEARCH,
    AgentCapability.PERPLEXITY,
]


# =============================================================================
# Test Scenarios
# =============================================================================

class TestScenario:
    """Individual test scenario configuration"""

    def __init__(
        self,
        name: str,
        description: str,
        task_description: str,
        required_capabilities: List[AgentCapability],
        priority: TaskPriority = TaskPriority.NORMAL,
    ):
        self.name = name
        self.description = description
        self.task_description = task_description
        self.required_capabilities = required_capabilities
        self.priority = priority


# Define test scenarios
TEST_SCENARIOS = [
    TestScenario(
        name="Simple Research",
        description="Test basic research capability",
        task_description="Find the current population of Cape Town, South Africa",
        required_capabilities=[AgentCapability.RESEARCH],
    ),
    TestScenario(
        name="Web Search",
        description="Test Kagi search capability",
        task_description=(
            "Use Kagi search to find recent news about renewable energy "
            "in South Africa"
        ),
        required_capabilities=[AgentCapability.SEARCH],
    ),
    TestScenario(
        name="Perplexity Research",
        description="Test Perplexity API integration",
        task_description=(
            "Use Perplexity to research the economic impact of tourism "
            "in Cape Town"
        ),
        required_capabilities=[AgentCapability.PERPLEXITY],
    ),
    TestScenario(
        name="Analysis Task",
        description="Test data analysis capability",
        task_description=(
            "Analyze the key factors contributing to Cape Town's water "
            "crisis and provide insights"
        ),
        required_capabilities=[AgentCapability.ANALYSIS],
    ),
    TestScenario(
        name="Writing Task",
        description="Test content generation",
        task_description=(
            "Write a 200-word summary about Table Mountain's biodiversity"
        ),
        required_capabilities=[AgentCapability.WRITING],
    ),
    TestScenario(
        name="Memory Task",
        description="Test knowledge storage and retrieval",
        task_description=(
            "Store the following fact in memory: Cape Town was founded "
            "in 1652 by Jan van Riebeeck"
        ),
        required_capabilities=[AgentCapability.MEMORY],
    ),
    TestScenario(
        name="Multi-Capability Task",
        description="Test agent with multiple capabilities",
        task_description=(
            "Research Cape Town's climate, analyze temperature trends, "
            "and write a brief report"
        ),
        required_capabilities=[
            AgentCapability.RESEARCH,
            AgentCapability.ANALYSIS,
            AgentCapability.WRITING,
        ],
    ),
    TestScenario(
        name="General Purpose Task",
        description="Test general capability",
        task_description="What is the time difference between Cape Town and New York?",
        required_capabilities=[AgentCapability.GENERAL],
    ),
    TestScenario(
        name="High Priority Task",
        description="Test priority handling",
        task_description=(
            "URGENT: Find the emergency contact number for Cape Town "
            "disaster management"
        ),
        required_capabilities=[AgentCapability.RESEARCH],
        priority=TaskPriority.HIGH,
    ),
]


# =============================================================================
# Agent Definitions
# =============================================================================

AGENT_DEFINITIONS = [
    {
        "name": "Research Specialist",
        "capabilities": [AgentCapability.RESEARCH],
        "instructions": (
            "You are a research specialist. Focus on gathering accurate, "
            "well-sourced information. Always cite your sources."
        ),
    },
    {
        "name": "Data Analyst",
        "capabilities": [AgentCapability.ANALYSIS],
        "instructions": (
            "You are a data analyst. Provide insights, identify patterns, "
            "and make data-driven recommendations."
        ),
    },
    {
        "name": "Content Writer",
        "capabilities": [AgentCapability.WRITING],
        "instructions": (
            "You are a content writer. Create clear, engaging, and "
            "well-structured content."
        ),
    },
    {
        "name": "Knowledge Manager",
        "capabilities": [AgentCapability.MEMORY],
        "instructions": (
            "You are a knowledge manager. Store and retrieve information "
            "efficiently using the memory system."
        ),
    },
    {
        "name": "Search Agent",
        "capabilities": [AgentCapability.SEARCH],
        "instructions": (
            "You are a search specialist using Kagi. Find relevant, "
            "up-to-date information from the web."
        ),
    },
    {
        "name": "Perplexity Agent",
        "capabilities": [AgentCapability.PERPLEXITY],
        "instructions": (
            "You are a research agent using Perplexity. Provide comprehensive, "
            "well-researched answers with proper citations."
        ),
    },
    {
        "name": "General Agent",
        "capabilities": [AgentCapability.GENERAL],
        "instructions": (
            "You are a general-purpose assistant. Handle various tasks "
            "efficiently."
        ),
    },
    {
        "name": "Multi-Skilled Agent",
        "capabilities": [
            AgentCapability.RESEARCH,
            AgentCapability.ANALYSIS,
            AgentCapability.WRITING,
        ],
        "instructions": (
            "You are a multi-skilled agent capable of research, analysis, "
            "and writing. Combine these skills effectively."
        ),
    },
]


# =============================================================================
# Test Runner
# =============================================================================

async def setup_test_environment():
    """Initialize test environment with agents"""
    logger.info("test_setup_started")

    # Initialize components
    cost_tracker = CostTracker()
    await cost_tracker.__aenter__()

    registry = AgentRegistry()
    pool = AgentPool(
        registry=registry,
        cost_tracker=cost_tracker,
        max_agents=20,
    )

    # Spawn all test agents
    agents = []
    for agent_def in AGENT_DEFINITIONS:
        try:
            agent = await pool.spawn_agent(
                name=agent_def["name"],
                capabilities=agent_def["capabilities"],
                specialized_instructions=agent_def["instructions"],
            )
            agents.append(agent)
            logger.info(
                "test_agent_created",
                name=agent_def["name"],
                capabilities=[c.value for c in agent_def["capabilities"]],
            )
        except Exception as e:
            logger.error(
                "test_agent_creation_failed",
                name=agent_def["name"],
                error=str(e),
            )

    logger.info("test_setup_completed", agent_count=len(agents))
    return pool, registry, cost_tracker, agents


async def run_single_test(
    scenario: TestScenario,
    pool: AgentPool,
    registry: AgentRegistry,
) -> dict:
    """Run a single test scenario"""
    logger.info(
        "test_scenario_started",
        name=scenario.name,
        description=scenario.description,
    )

    # Find capable agents
    all_agents = await registry.list_agents()
    capable_agents = []

    for agent_meta in all_agents:
        if all(
            cap in agent_meta.capabilities
            for cap in scenario.required_capabilities
        ):
            capable_agents.append(agent_meta)

    if not capable_agents:
        logger.warning(
            "no_capable_agents",
            scenario=scenario.name,
            required_caps=[c.value for c in scenario.required_capabilities],
        )
        return {
            "scenario": scenario.name,
            "success": False,
            "error": "No capable agents available",
        }

    # Select first capable agent
    selected_agent_meta = capable_agents[0]
    agent = pool._agents.get(selected_agent_meta.agent_id)

    if not agent:
        return {
            "scenario": scenario.name,
            "success": False,
            "error": "Agent not found in pool",
        }

    # Create task
    from datetime import datetime
    import uuid

    task = Task(
        task_id=str(uuid.uuid4()),
        description=scenario.task_description,
        required_capabilities=scenario.required_capabilities,
        priority=scenario.priority,
        created_at=datetime.now(),
        status="pending",
        user_id=TEST_USER_ID,
    )

    # Execute task
    try:
        result = await agent.execute_task(task)

        return {
            "scenario": scenario.name,
            "success": result.success,
            "agent": selected_agent_meta.name,
            "agent_id": selected_agent_meta.agent_id,
            "duration": result.duration_seconds,
            "cost": result.cost,
            "result": result.result[:200] if result.result else None,
            "citations": len(result.citations) if result.citations else 0,
            "error": result.error,
        }
    except Exception as e:
        logger.error(
            "test_execution_failed",
            scenario=scenario.name,
            error=str(e),
        )
        return {
            "scenario": scenario.name,
            "success": False,
            "error": str(e),
        }


async def run_all_tests():
    """Run all test scenarios"""
    logger.info("test_suite_started", scenario_count=len(TEST_SCENARIOS))

    # Setup
    pool, registry, cost_tracker, agents = await setup_test_environment()

    # Run tests
    results = []
    for scenario in TEST_SCENARIOS:
        result = await run_single_test(scenario, pool, registry)
        results.append(result)

        # Brief pause between tests
        await asyncio.sleep(1)

    # Cleanup
    await cleanup_test_environment(pool, cost_tracker)

    # Summary
    print_test_summary(results)

    return results


async def cleanup_test_environment(pool: AgentPool, cost_tracker: CostTracker):
    """Clean up test environment"""
    logger.info("test_cleanup_started")

    try:
        # Cleanup pool
        await pool.cleanup()

        # Cleanup cost tracker
        await cost_tracker.__aexit__(None, None, None)

        logger.info("test_cleanup_completed")
    except Exception as e:
        logger.error("test_cleanup_failed", error=str(e))


def print_test_summary(results: List[dict]):
    """Print formatted test summary"""
    print("\n" + "=" * 80)
    print("TEST SUITE SUMMARY")
    print("=" * 80)

    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed

    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%\n")

    print("-" * 80)
    print(f"{'Scenario':<30} {'Status':<10} {'Agent':<20} {'Duration':<10}")
    print("-" * 80)

    for result in results:
        status = "✓ PASS" if result["success"] else "✗ FAIL"
        agent = result.get("agent", "N/A")[:18]
        duration = f"{result.get('duration', 0):.2f}s" if result.get("duration") else "N/A"

        print(f"{result['scenario']:<30} {status:<10} {agent:<20} {duration:<10}")

    print("-" * 80)

    # Show failures
    failures = [r for r in results if not r["success"]]
    if failures:
        print("\nFAILURE DETAILS:")
        print("-" * 80)
        for result in failures:
            print(f"\nScenario: {result['scenario']}")
            print(f"Error: {result.get('error', 'Unknown error')}")

    # Show cost summary
    total_cost = sum(r.get("cost", 0) for r in results if r["success"])
    print(f"\nTotal Cost: ${total_cost:.4f}")
    print("=" * 80 + "\n")


# =============================================================================
# Interactive Test Functions
# =============================================================================

async def test_single_capability(capability: AgentCapability):
    """Test a single capability"""
    scenarios = [s for s in TEST_SCENARIOS if capability in s.required_capabilities]

    if not scenarios:
        print(f"No test scenarios found for capability: {capability.value}")
        return

    pool, registry, cost_tracker, agents = await setup_test_environment()

    results = []
    for scenario in scenarios:
        result = await run_single_test(scenario, pool, registry)
        results.append(result)

    await cleanup_test_environment(pool, cost_tracker)
    print_test_summary(results)

    return results


async def test_agent_pool_limits():
    """Test agent pool capacity and limits"""
    logger.info("testing_agent_pool_limits")

    registry = AgentRegistry()
    pool = AgentPool(registry=registry, max_agents=3)

    # Try to spawn more than max agents
    try:
        for i in range(5):
            await pool.spawn_agent(
                name=f"Test Agent {i}",
                capabilities=[AgentCapability.GENERAL],
            )
    except RuntimeError as e:
        logger.info("expected_error_caught", error=str(e))
        print(f"✓ Pool limit enforced: {e}")

    await pool.cleanup()


async def test_concurrent_execution():
    """Test concurrent task execution"""
    logger.info("testing_concurrent_execution")

    pool, registry, cost_tracker, agents = await setup_test_environment()

    # Create multiple tasks
    scenarios = TEST_SCENARIOS[:5]  # First 5 scenarios
    tasks = [run_single_test(s, pool, registry) for s in scenarios]

    # Execute concurrently
    results = await asyncio.gather(*tasks)

    await cleanup_test_environment(pool, cost_tracker)
    print_test_summary(results)

    return results


# =============================================================================
# Main Entry Point
# =============================================================================

async def main():
    """Main test runner"""
    print("\n" + "=" * 80)
    print("MULTI-AGENT ORCHESTRATION SYSTEM - CAPABILITY TEST SUITE")
    print("=" * 80 + "\n")

    print("Available Test Modes:")
    print("1. Run all tests")
    print("2. Test specific capability")
    print("3. Test agent pool limits")
    print("4. Test concurrent execution")
    print("5. Quick smoke test")

    # For now, run all tests
    print("\nRunning: ALL TESTS\n")
    results = await run_all_tests()

    return results


if __name__ == "__main__":
    # Run tests
    asyncio.run(main())
