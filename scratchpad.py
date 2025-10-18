import asyncio
from datetime import datetime
from src.orchestration.worker_agent import WorkerAgent
from src.orchestration.models import AgentCapability, Task, TaskPriority, TaskStatus
from src.services.cost_tracker import CostTracker
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


async def main():
    """Example: Using Kagi Search through a WorkerAgent"""

    # Initialize cost tracker
    cost_tracker = CostTracker()

    # Create a research-focused worker agent with search capabilities
    async with WorkerAgent(
            agent_id="research-agent-001",
            name="Research Specialist",
            capabilities=[
                AgentCapability.SEARCH,
                AgentCapability.RESEARCH,
                AgentCapability.GENERAL,
            ],
            cost_tracker=cost_tracker,
            specialized_instructions="""You are a research specialist with access to Kagi FastGPT.
Use Kagi search for comprehensive, accurate answers backed by live web data.
Always cite your sources and provide thorough analysis."""
    ) as agent:

        # Create a research task with all required fields
        task = Task(
            task_id="task-001",
            description="What's new in AI? Provide a comprehensive overview of recent developments.",
            required_capabilities=[AgentCapability.SEARCH, AgentCapability.RESEARCH],
            priority=TaskPriority.NORMAL,
            created_at=datetime.now(),
            status=TaskStatus.PENDING,
            user_id="demo-user"
        )

        print("🤖 Starting agent task execution...")
        print(f"📋 Task: {task.description}\n")

        # Execute the task (agent will use Kagi search automatically)
        result = await agent.execute_task(task)

        # Display results
        if result.success:
            print("✅ Task completed successfully!\n")
            print("📝 Response:")
            print("=" * 80)
            print(result.result)
            print("=" * 80)

            if result.citations:
                print("\n📚 Sources:")
                for i, citation in enumerate(result.citations, 1):
                    print(f"  {i}. {citation}")

            print(f"\n💰 Cost: ${result.cost:.4f}")
            print(f"⏱️  Duration: {result.duration_seconds:.2f}s")

            # Display cost summary
            costs = await cost_tracker.get_user_costs("demo-user")
            print(f"\n💵 Total Daily Cost: ${costs['total']:.4f}")
            print(f"📊 Remaining Budget: ${costs['remaining']:.2f}")
        else:
            print(f"❌ Task failed: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())