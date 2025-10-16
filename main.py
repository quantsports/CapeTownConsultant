# Remove the AutonomousAssistant class from main.py
# Instead, import it from src.interface.assistant

import asyncio
from src.interface.assistant import AutonomousAssistant
from src.services.cost_tracker import CostTracker
from src.core.logging import logger

async def main():
    """Main entry point for CLI"""
    cost_tracker = CostTracker()

    async with AutonomousAssistant(cost_tracker=cost_tracker) as assistant:
        logger.info("assistant_ready", message="Cape Town Consultant ready!")
        print("\n🌍 Cape Town Consultant (CLI)")
        print("Type your questions or 'exit' to quit\n")

        while True:
            try:
                user_input = input("You: ").strip()

                if user_input.lower() in ['exit', 'quit', 'q']:
                    break

                if not user_input:
                    continue

                response = await assistant.chat(user_input)
                print(f"\nAssistant: {response}\n")

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error("chat_error", error=str(e))
                print(f"\n❌ Error: {e}\n")

if __name__ == "__main__":
    asyncio.run(main())