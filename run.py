#!/usr/bin/env python3
"""
Quick Prototyping Terminal - CapeTownConsultant
A simple, interactive terminal for rapid testing and development

Usage:
    python quick_prototype.py

Commands:
    /help       - Show this help
    /clear      - Clear conversation
    /config     - Show configuration
    /costs      - Show cost usage
    /user <id>  - Switch user
    /memory     - Query user memories
    /profile    - Show user profile
    /debug on   - Enable debug mode
    /debug off  - Disable debug mode
    /exit       - Exit application

Features:
    - Color-coded output
    - Auto-save conversation
    - Quick access to all tools
    - Debug mode for troubleshooting
"""

import asyncio
import sys
from datetime import datetime
from typing import Optional

# Add color support
try:
    from colorama import init, Fore, Style

    init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False


    # Fallback to no colors
    class Fore:
        GREEN = CYAN = YELLOW = RED = MAGENTA = BLUE = WHITE = ""


    class Style:
        BRIGHT = RESET_ALL = ""

from src import AutonomousAssistant, Config
from src.core.logging import logger


class QuickPrototype:
    """Interactive terminal for quick prototyping"""

    def __init__(self):
        self.assistant: Optional[AutonomousAssistant] = None
        self.current_user = "proto_user"
        self.debug_mode = False
        self.session_start = datetime.now()
        self.message_count = 0

    def print_banner(self):
        """Print startup banner"""
        banner = f"""
{Fore.CYAN}{Style.BRIGHT}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║           🧠 CAPETOWN CONSULTANT - QUICK PROTOTYPE           ║
║                      v3.0 - Terminal Mode                    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.GREEN}✓ Ready for rapid prototyping and testing{Style.RESET_ALL}
{Fore.YELLOW}⚡ Type /help for commands{Style.RESET_ALL}
"""
        print(banner)

    def print_help(self):
        """Print help message"""
        help_text = f"""
{Fore.CYAN}{Style.BRIGHT}Available Commands:{Style.RESET_ALL}

{Fore.GREEN}Basic:{Style.RESET_ALL}
  /help              Show this help message
  /exit, /quit       Exit the application
  /clear             Clear conversation history

{Fore.GREEN}Information:{Style.RESET_ALL}
  /config            Show API configuration status
  /costs             Show cost usage for current user
  /stats             Show session statistics
  /user <id>         Switch to different user ID

{Fore.GREEN}Memory & Profile:{Style.RESET_ALL}
  /memory            Show recent memories for current user
  /memory <query>    Search memories with query
  /profile           Show user profile
  /profile set <k=v> Update profile (e.g., /profile set name=John)

{Fore.GREEN}Development:{Style.RESET_ALL}
  /debug on          Enable debug logging
  /debug off         Disable debug logging
  /test search       Test search functionality
  /test memory       Test memory functionality
  /test all          Run all tests

{Fore.GREEN}Tips:{Style.RESET_ALL}
  • Just type naturally to chat with the assistant
  • The assistant will automatically use tools as needed
  • Citations are shown as [1], [2], etc.
  • Costs are tracked per user
  • Type multi-line by ending with \\
"""
        print(help_text)

    def print_config(self):
        """Print configuration status"""
        status = Config.validate_required_keys()

        print(f"\n{Fore.CYAN}{Style.BRIGHT}Configuration Status:{Style.RESET_ALL}\n")

        items = [
            ("OpenAI", status['openai'], "Required - Chat & Embeddings"),
            ("Pinecone", status['pinecone'], "Optional - Vector Memory"),
            ("SerpAPI", status['serpapi'], "Optional - Web Search"),
            ("Google Search", status['google_search'], "Optional - Alternative Search"),
            ("Perplexity", status['perplexity'], "Optional - Complex Analysis"),
        ]

        for name, configured, description in items:
            icon = f"{Fore.GREEN}✓" if configured else f"{Fore.RED}✗"
            print(f"  {icon} {name:<20} {Style.RESET_ALL}{Fore.WHITE}{description}{Style.RESET_ALL}")

        print(f"\n{Fore.YELLOW}Settings:{Style.RESET_ALL}")
        print(f"  • Daily Budget: ${Config.DAILY_BUDGET_LIMIT:.2f}")
        print(f"  • Memory Threshold: {Config.MEMORY_SIMILARITY_THRESHOLD}")
        print(f"  • Auto-Memory: {'Enabled' if Config.AUTO_MEMORY_EXTRACTION else 'Disabled'}")
        print()

    async def print_costs(self):
        """Print cost information"""
        costs = await self.assistant.get_costs(self.current_user)

        used = costs['total']
        limit = costs['limit']
        remaining = costs['remaining']
        percentage = (used / limit * 100) if limit > 0 else 0

        print(f"\n{Fore.CYAN}{Style.BRIGHT}Cost Usage - {self.current_user}:{Style.RESET_ALL}\n")
        print(f"  Used:      ${used:.4f}")
        print(f"  Limit:     ${limit:.2f}")
        print(f"  Remaining: ${remaining:.4f}")

        # Progress bar
        bar_length = 40
        filled = int(bar_length * percentage / 100)
        bar = "█" * filled + "░" * (bar_length - filled)

        if percentage < 50:
            color = Fore.GREEN
        elif percentage < 80:
            color = Fore.YELLOW
        else:
            color = Fore.RED

        print(f"  {color}[{bar}] {percentage:.1f}%{Style.RESET_ALL}\n")

    def print_stats(self):
        """Print session statistics"""
        duration = (datetime.now() - self.session_start).total_seconds()
        minutes = int(duration // 60)
        seconds = int(duration % 60)

        print(f"\n{Fore.CYAN}{Style.BRIGHT}Session Statistics:{Style.RESET_ALL}\n")
        print(f"  User:         {self.current_user}")
        print(f"  Duration:     {minutes}m {seconds}s")
        print(f"  Messages:     {self.message_count}")
        print(f"  Started:      {self.session_start.strftime('%H:%M:%S')}")
        print()

    async def show_memories(self, query: Optional[str] = None):
        """Show user memories"""
        print(f"\n{Fore.CYAN}{Style.BRIGHT}Searching memories...{Style.RESET_ALL}\n")

        # Import here to avoid circular imports
        from src.memory import VectorMemory
        from src.services.embedding import EmbeddingService
        from src.services.cost_tracker import CostTracker

        cost_tracker = CostTracker()
        embedding_service = EmbeddingService(cost_tracker=cost_tracker)
        vector_memory = VectorMemory(embedding_service)

        namespace = f"user:{self.current_user}"
        search_query = query or "user preferences and information"

        result = await vector_memory.query(
            search_query,
            namespace,
            top_k=5,
            user_id=self.current_user
        )

        if result.success and result.data.get('matches'):
            matches = result.data['matches']
            print(f"Found {len(matches)} memories:\n")

            for i, match in enumerate(matches, 1):
                score = match.get('score', 0)
                text = match.get('text', '')
                timestamp = match.get('timestamp', 'Unknown')

                print(f"{Fore.GREEN}{i}. [{score:.2f}]{Style.RESET_ALL} {text}")
                print(f"   {Fore.WHITE}({timestamp}){Style.RESET_ALL}\n")
        else:
            print(f"{Fore.YELLOW}No memories found.{Style.RESET_ALL}\n")

    async def show_profile(self):
        """Show user profile"""
        from src.memory import ProfileManager

        profile_manager = ProfileManager()
        profile = await profile_manager.read(self.current_user)

        print(f"\n{Fore.CYAN}{Style.BRIGHT}User Profile - {self.current_user}:{Style.RESET_ALL}\n")

        if profile:
            for key, value in profile.items():
                print(f"  {Fore.GREEN}{key}:{Style.RESET_ALL} {value}")
        else:
            print(f"  {Fore.YELLOW}No profile data found.{Style.RESET_ALL}")
        print()

    async def update_profile(self, key_value: str):
        """Update user profile"""
        try:
            key, value = key_value.split('=', 1)
            key = key.strip()
            value = value.strip()

            from src.memory import ProfileManager
            profile_manager = ProfileManager()

            success = await profile_manager.write(self.current_user, {key: value})

            if success:
                print(f"{Fore.GREEN}✓ Profile updated: {key} = {value}{Style.RESET_ALL}\n")
            else:
                print(f"{Fore.RED}✗ Failed to update profile{Style.RESET_ALL}\n")
        except ValueError:
            print(f"{Fore.RED}✗ Invalid format. Use: /profile set key=value{Style.RESET_ALL}\n")

    async def run_tests(self, test_type: str = "all"):
        """Run quick tests"""
        print(f"\n{Fore.CYAN}{Style.BRIGHT}Running tests...{Style.RESET_ALL}\n")

        if test_type in ["search", "all"]:
            print(f"{Fore.YELLOW}Testing search...{Style.RESET_ALL}")
            response = await self.assistant.chat(
                "What is the capital of France?",
                self.current_user
            )
            print(f"{Fore.GREEN}✓ Search test passed{Style.RESET_ALL}\n")

        if test_type in ["memory", "all"]:
            print(f"{Fore.YELLOW}Testing memory...{Style.RESET_ALL}")
            await self.show_memories()
            print(f"{Fore.GREEN}✓ Memory test passed{Style.RESET_ALL}\n")

        print(f"{Fore.GREEN}{Style.BRIGHT}✓ All tests completed{Style.RESET_ALL}\n")

    async def process_command(self, command: str) -> bool:
        """Process command. Returns False to exit."""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else None

        if cmd in ['/exit', '/quit']:
            return False

        elif cmd == '/help':
            self.print_help()

        elif cmd == '/clear':
            self.assistant.clear_history()
            print(f"{Fore.GREEN}✓ Conversation cleared{Style.RESET_ALL}\n")

        elif cmd == '/config':
            self.print_config()

        elif cmd == '/costs':
            await self.print_costs()

        elif cmd == '/stats':
            self.print_stats()

        elif cmd == '/user':
            if arg:
                self.current_user = arg
                print(f"{Fore.GREEN}✓ Switched to user: {arg}{Style.RESET_ALL}\n")
            else:
                print(f"{Fore.YELLOW}Current user: {self.current_user}{Style.RESET_ALL}\n")

        elif cmd == '/memory':
            await self.show_memories(arg)

        elif cmd == '/profile':
            if arg and arg.startswith('set '):
                await self.update_profile(arg[4:])
            else:
                await self.show_profile()

        elif cmd == '/debug':
            if arg == 'on':
                self.debug_mode = True
                print(f"{Fore.GREEN}✓ Debug mode enabled{Style.RESET_ALL}\n")
            elif arg == 'off':
                self.debug_mode = False
                print(f"{Fore.GREEN}✓ Debug mode disabled{Style.RESET_ALL}\n")
            else:
                print(f"{Fore.YELLOW}Usage: /debug [on|off]{Style.RESET_ALL}\n")

        elif cmd == '/test':
            await self.run_tests(arg or "all")

        else:
            print(f"{Fore.RED}✗ Unknown command: {cmd}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Type /help for available commands{Style.RESET_ALL}\n")

        return True

    async def chat_loop(self):
        """Main chat loop"""
        self.print_banner()
        self.print_config()

        # Initialize assistant
        print(f"{Fore.YELLOW}Initializing assistant...{Style.RESET_ALL}")
        async with AutonomousAssistant() as assistant:
            self.assistant = assistant
            print(f"{Fore.GREEN}✓ Ready!{Style.RESET_ALL}\n")

            while True:
                try:
                    # Prompt
                    prompt = f"{Fore.MAGENTA}{Style.BRIGHT}[{self.current_user}] You>{Style.RESET_ALL} "
                    user_input = input(prompt).strip()

                    if not user_input:
                        continue

                    # Handle commands
                    if user_input.startswith('/'):
                        should_continue = await self.process_command(user_input)
                        if not should_continue:
                            break
                        continue

                    # Multi-line input support
                    while user_input.endswith('\\'):
                        user_input = user_input[:-1] + '\n'
                        user_input += input('... ').strip()

                    # Send to assistant
                    print(f"\n{Fore.CYAN}🤖 Assistant:{Style.RESET_ALL}\n")

                    response = await self.assistant.chat(user_input, self.current_user)

                    # Print response with formatting
                    print(f"{Fore.WHITE}{response}{Style.RESET_ALL}\n")

                    self.message_count += 1

                except KeyboardInterrupt:
                    print(f"\n\n{Fore.YELLOW}Use /exit to quit{Style.RESET_ALL}\n")
                    continue

                except Exception as e:
                    print(f"\n{Fore.RED}✗ Error: {e}{Style.RESET_ALL}\n")
                    if self.debug_mode:
                        import traceback
                        traceback.print_exc()

        # Goodbye
        print(f"\n{Fore.CYAN}{Style.BRIGHT}Session Summary:{Style.RESET_ALL}")
        self.print_stats()
        await self.print_costs()
        print(f"{Fore.GREEN}👋 Goodbye!{Style.RESET_ALL}\n")


async def main():
    """Entry point"""
    prototype = QuickPrototype()
    await prototype.chat_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)