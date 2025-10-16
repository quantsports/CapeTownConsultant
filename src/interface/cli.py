"""
CLI interface with full orchestration support
Fixed to properly control and display orchestration status
"""

import asyncio
from src.interface.assistant import AutonomousAssistant
from src.config.settings import Config
from src.workers.templates import WorkerType, WorkerTemplates


async def run_cli():
    """Run the CLI interface with orchestration support"""
    print("🧠 Autonomous Assistant v3.1 (Multi-Agent Orchestration)")
    print("=" * 70)
    print("✅ Features: Multi-agent orchestration, Domain specialists")
    print("=" * 70)
    print("\nCommands:")
    print("  exit      - Exit the program")
    print("  clear     - Clear conversation history")
    print("  config    - Show configuration")
    print("  costs     - Show cost summary")
    print("  mode      - Toggle orchestration mode")
    print("  workers   - List available workers")
    print("  status    - Show current mode and status")
    print()

    user_id = "cli_user"
    orchestration_enabled = True  # Start with orchestration enabled

    async with AutonomousAssistant(enable_orchestration=orchestration_enabled) as assistant:
        try:
            while True:
                try:
                    # Dynamic mode indicator
                    mode_status = assistant.get_orchestration_status()
                    mode_indicator = "🎭" if mode_status else "🤖"
                    mode_text = "ORCHESTRATION" if mode_status else "TRADITIONAL"

                    user_input = input(f"\n{mode_indicator} [{mode_text}] You: ").strip()

                    if not user_input:
                        continue

                    # Handle commands
                    if user_input.lower() == 'exit':
                        costs = await assistant.get_costs(user_id)
                        print(f"\n💰 Final costs: ${costs['total']:.4f}")
                        print("👋 Goodbye!")
                        break

                    elif user_input.lower() == 'clear':
                        assistant.clear_history()
                        print("✅ Conversation history cleared")
                        continue

                    elif user_input.lower() == 'config':
                        print("\n📋 Configuration:")
                        print(f"  OpenAI API: {'✅ Configured' if Config.OPENAI_API_KEY else '❌ Missing'}")
                        print(f"  Pinecone: {'✅ Configured' if Config.PINECONE_API_KEY else '⚠️  Optional'}")
                        print(f"  SerpAPI: {'✅ Configured' if Config.SERPAPI_API_KEY else '⚠️  Optional'}")
                        print(f"  Model: {Config.CHAT_MODEL}")
                        print(f"  Max Iterations: {Config.MAX_ITERATIONS}")
                        print(f"  Orchestration: {'✅ Enabled' if assistant.get_orchestration_status() else '❌ Disabled'}")
                        continue

                    elif user_input.lower() == 'costs':
                        costs = await assistant.get_costs(user_id)
                        print(f"\n💰 Cost Summary:")
                        print(f"  Total: ${costs['total']:.4f}")
                        print(f"  Limit: ${costs['limit']:.2f}")
                        print(f"  Remaining: ${costs['limit'] - costs['total']:.2f}")
                        continue

                    elif user_input.lower() == 'mode':
                        current = assistant.get_orchestration_status()
                        assistant.toggle_orchestration(not current)
                        new_mode = "ORCHESTRATION" if not current else "TRADITIONAL"
                        print(f"✅ Switched to {new_mode} mode")
                        continue

                    elif user_input.lower() == 'workers':
                        print("\n👥 Available Workers:")
                        print()
                        for worker_type in WorkerType:
                            template = WorkerTemplates.get_template(worker_type)
                            name = worker_type.value.replace('_', ' ').title()
                            priority = template.get('priority', 3)
                            tools = template.get('tools', [])
                            print(f"  {name}")
                            print(f"    Priority: {priority} | Tools: {', '.join(tools)}")
                        print()
                        continue

                    elif user_input.lower() == 'status':
                        mode = "ORCHESTRATION" if assistant.get_orchestration_status() else "TRADITIONAL"
                        costs = await assistant.get_costs(user_id)
                        print(f"\n📊 Current Status:")
                        print(f"  Mode: {mode}")
                        print(f"  User ID: {user_id}")
                        print(f"  Costs: ${costs['total']:.4f} / ${costs['limit']:.2f}")
                        print(f"  Model: {Config.CHAT_MODEL}")
                        continue

                    # Process normal chat message
                    print()  # Add spacing
                    response = await assistant.chat(user_input, user_id)
                    print(f"\n{response}")

                except KeyboardInterrupt:
                    print("\n⚠️  Interrupted. Type 'exit' to quit.")
                    continue

                except Exception as e:
                    print(f"\n❌ Error: {str(e)}")
                    continue

        except Exception as e:
            print(f"\n💥 Fatal error: {str(e)}")
            raise


def main():
    """Entry point"""
    asyncio.run(run_cli())


if __name__ == "__main__":
    main()