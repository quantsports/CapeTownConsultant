"""
CLI interface
Command-line interface for the assistant
"""

import asyncio
from src.interface.assistant import AutonomousAssistant
from src.config.settings import Config


async def run_cli():
    """Run the CLI interface"""
    print("🧠 Autonomous Assistant v3.0 (Enhanced)")
    print("=" * 70)
    print("✅ Fixes: #1,#2,#3,#4,#6,#7,#8,#9,#10")
    print("=" * 70)
    print("\nCommands: exit | clear | config | costs\n")

    user_id = "cli_user"

    async with AutonomousAssistant() as assistant:
        try:
            while True:
                try:
                    user_input = input("\n🧑 You: ").strip()

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