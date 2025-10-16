"""
CLI interface
Command-line interface for the assistant with orchestration support
"""

import asyncio
from src.interface.assistant import AutonomousAssistant
from src.config.settings import Config


async def run_cli():
    """Run the CLI interface"""
    print("🧠 Autonomous Assistant v3.1 (Multi-Agent Orchestration)")
    print("=" * 70)
    print("✅ Features: Multi-agent orchestration, Domain specialists")
    print("=" * 70)
    print("\nCommands: exit | clear | config | costs | mode | workers\n")

    user_id = "cli_user"
    orchestration_enabled = True

    async with AutonomousAssistant(enable_orchestration=orchestration_enabled) as assistant:
        try:
            while True:
                try:
                    mode_indicator = "🎭" if orchestration_enabled else "🤖"
                    user_input = input(f"\n{mode_indicator} You: ").strip()

                    if not user_input:
                        continue

                    if user_input.lower() == 'exit':
                        costs = await assistant.get_costs(user_id)
                        print(f"\n💰 Final: ${costs['total']:.4f}")
                        print("👋 Goodbye!")
                        break

                    if user_input.lower() == 'clear':
                        assistant.clear_history()
                        print("✅ History cleared")
                        continue

                    if user_input.lower() == 'costs':
                        costs = await assistant.get_costs(user_id)
                        print(f"\n💰 Today: ${costs['total']:.4f} / ${costs['limit']:.2f}")
                        continue

                    if user_input.lower() == 'config':
                        print("\n📋 Status:")
                        status = Config.validate_required_keys()
                        print(f"  OpenAI: {'✅' if status['openai'] else '❌'}")
                        print(f"  Pinecone: {'✅' if status['pinecone'] else '❌'}")
                        print(f"  SerpAPI: {'✅' if status['serpapi'] else '❌'}")
                        print(f"  Google: {'✅' if status['google_search'] else '❌'}")
                        print(f"  Perplexity: {'✅' if status['perplexity'] else '❌'}")
                        continue

                    if user_input.lower() == 'mode':
                        orchestration_enabled = not orchestration_enabled
                        assistant.toggle_orchestration(orchestration_enabled)
                        mode_name = "ORCHESTRATION" if orchestration_enabled else "TRADITIONAL"
                        print(f"✅ Switched to {mode_name} mode")
                        continue

                    if user_input.lower() == 'workers':
                        from src.workers.templates import WorkerType, WorkerTemplates
                        print("\n👥 Available Specialists:")
                        for wt in WorkerType:
                            template = WorkerTemplates.get_template(wt)
                            if template:
                                print(f"  • {wt.value.replace('_', ' ').title()} (Priority: {template.get('priority', 3)})")
                        continue

                    print("\n🤔 Processing...\n")
                    response = await assistant.chat(user_input, user_id)
                    print(f"🤖 Assistant:\n\n{response}")

                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")

        except Exception as e:
            print(f"Fatal: {e}")


def main():
    """Entry point for CLI"""
    asyncio.run(run_cli())


if __name__ == "__main__":
    main()