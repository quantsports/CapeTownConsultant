"""
Main test script for CapeTownConsultant
Simulates user interactions and verifies tool functionality
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import json

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.interface.assistant import AutonomousAssistant
from src.services.cost_tracker import CostTracker
from src.config.settings import Config
from src.core.logging import logger


# Terminal colors for better output
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class TestRunner:
    """Comprehensive test runner for the assistant"""

    def __init__(self):
        self.test_user_id = f"test_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.results: List[Dict[str, Any]] = []
        self.assistant: AutonomousAssistant = None
        self.cost_tracker: CostTracker = None

        # Test queries designed to trigger specific tools
        self.test_queries = [
            {
                "query": "Store this in memory: I prefer Italian cuisine and love pasta dishes",
                "expected_tool": "memory_upsert",
                "description": "Memory storage test - user preference",
            },
            {
                "query": "Remember: My favorite restaurant style is casual fine dining",
                "expected_tool": "memory_upsert",
                "description": "Memory storage test - preference storage",
            },
            {
                "query": "What are my food preferences?",
                "expected_tool": "memory_query",
                "description": "Memory retrieval test - recall stored preferences",
            },
            {
                "query": "What are the current restaurant trends in Cape Town?",
                "expected_tool": "web_search",
                "description": "Web search test - SerpAPI for recent trends",
            },
            {
                "query": "Find information about the best Italian restaurants in South Africa",
                "expected_tool": "web_search",
                "description": "Web search test - SerpAPI for restaurant info",
            },
            {
                "query": "What are the latest food safety regulations for restaurants in 2024?",
                "expected_tool": "perplexity_search",
                "description": "Perplexity test - complex regulatory query",
            },
            {
                "query": "Analyze the future of ghost kitchens and their impact on traditional dining",
                "expected_tool": "perplexity_search",
                "description": "Perplexity test - analytical query",
            },
            {
                "query": "What did I say about my food preferences earlier?",
                "expected_tool": "memory_query",
                "description": "Memory recall test - verify persistence",
            },
            {
                "query": "Search for average restaurant startup costs in South Africa",
                "expected_tool": "web_search",
                "description": "Web search test - financial information",
            },
            {
                "query": "Store this: I'm planning to open a restaurant with a budget of $200k",
                "expected_tool": "memory_upsert",
                "description": "Memory storage test - business information",
            },
            {
                "query": "What is my restaurant budget and food preferences?",
                "expected_tool": "memory_query",
                "description": "Memory retrieval test - multiple facts",
            },
            {
                "query": "Give me a comprehensive analysis of sustainable restaurant practices",
                "expected_tool": "perplexity_search",
                "description": "Perplexity test - comprehensive analysis",
            },
        ]

    def print_header(self, text: str):
        """Print formatted header"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.HEADER}{text.center(80)}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.RESET}\n")

    def print_section(self, text: str):
        """Print formatted section"""
        print(f"\n{Colors.CYAN}{Colors.BOLD}{text}{Colors.RESET}")
        print(f"{Colors.CYAN}{'-' * 80}{Colors.RESET}")

    def print_success(self, text: str):
        """Print success message"""
        print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

    def print_error(self, text: str):
        """Print error message"""
        print(f"{Colors.RED}✗ {text}{Colors.RESET}")

    def print_info(self, text: str):
        """Print info message"""
        print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")

    def print_warning(self, text: str):
        """Print warning message"""
        print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

    async def initialize_assistant(self) -> bool:
        """Initialize the assistant with proper error handling"""
        self.print_section("🔧 Initializing Assistant")

        try:
            # Validate configuration
            if not Config.OPENAI_API_KEY:
                self.print_error("OPENAI_API_KEY not configured")
                return False

            self.print_info("OpenAI API key found")

            # Check optional APIs
            optional_apis = {
                "Pinecone": Config.PINECONE_API_KEY,
                "SerpAPI": Config.SERPAPI_API_KEY,
                "Perplexity": Config.PERPLEXITY_API_KEY,
                "Google Search": Config.GOOGLE_SEARCH_API_KEY,
            }

            for name, key in optional_apis.items():
                if key:
                    self.print_success(f"{name} configured")
                else:
                    self.print_warning(f"{name} not configured (optional)")

            # Initialize cost tracker
            self.cost_tracker = CostTracker()
            self.print_success("Cost tracker initialized")

            # Initialize assistant
            self.print_info("Initializing autonomous assistant...")
            self.assistant = await AutonomousAssistant(
                cost_tracker=self.cost_tracker
            ).__aenter__()

            self.print_success("Assistant initialized successfully")
            return True

        except Exception as e:
            self.print_error(f"Initialization failed: {str(e)}")
            logger.error("assistant_init_failed", error=str(e))
            return False

    async def cleanup_assistant(self):
        """Cleanup assistant resources"""
        if self.assistant:
            try:
                await self.assistant.__aexit__(None, None, None)
                self.print_success("Assistant cleanup completed")
            except Exception as e:
                self.print_warning(f"Cleanup warning: {str(e)}")

    async def execute_query(
        self, test_case: Dict[str, str], index: int
    ) -> Dict[str, Any]:
        """Execute a single test query"""
        query = test_case["query"]
        expected_tool = test_case["expected_tool"]
        description = test_case["description"]

        self.print_section(f"Test {index + 1}/12: {description}")
        self.print_info(f"Query: {query}")
        self.print_info(f"Expected tool: {expected_tool}")

        start_time = datetime.now()
        result = {
            "index": index + 1,
            "query": query,
            "description": description,
            "expected_tool": expected_tool,
            "start_time": start_time.isoformat(),
            "success": False,
            "response": None,
            "error": None,
            "duration_seconds": 0,
        }

        try:
            # Execute query
            response = await asyncio.wait_for(
                self.assistant.chat(query, self.test_user_id), timeout=120.0
            )

            duration = (datetime.now() - start_time).total_seconds()
            result["duration_seconds"] = round(duration, 2)
            result["response"] = response
            result["success"] = True

            # Analyze response
            response_lower = response.lower()

            # Check for error indicators
            if "error" in response_lower or "failed" in response_lower:
                result["success"] = False
                result["error"] = "Response contains error indicators"
                self.print_error(f"Query failed: {response[:200]}")
            else:
                self.print_success(f"Query completed in {duration:.2f}s")

                # Display response preview
                preview = response[:300] + "..." if len(response) > 300 else response
                print(f"\n{Colors.CYAN}Response preview:{Colors.RESET}")
                print(f"{preview}\n")

                # Tool verification
                if expected_tool in ["memory_upsert", "memory_query"]:
                    if (
                        "stored" in response_lower
                        or "remember" in response_lower
                        or "preference" in response_lower
                    ):
                        self.print_success("Memory operation detected")
                    else:
                        self.print_warning("Memory operation unclear")

                elif expected_tool == "web_search":
                    if "source" in response_lower or "[" in response:
                        self.print_success("Web search citations detected")
                    else:
                        self.print_warning("No citations detected")

                elif expected_tool == "perplexity_search":
                    if len(response) > 200:
                        self.print_success("Comprehensive response from Perplexity")
                    else:
                        self.print_warning("Response shorter than expected")

        except asyncio.TimeoutError:
            duration = (datetime.now() - start_time).total_seconds()
            result["duration_seconds"] = round(duration, 2)
            result["error"] = "Query timed out after 120 seconds"
            self.print_error("Query timed out")

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            result["duration_seconds"] = round(duration, 2)
            result["error"] = str(e)
            self.print_error(f"Query failed: {str(e)}")
            logger.error("query_execution_failed", query=query, error=str(e))

        return result

    async def get_cost_summary(self) -> Dict[str, float]:
        """Get cost summary for test user"""
        try:
            costs = await self.assistant.get_costs(self.test_user_id)
            return costs
        except Exception as e:
            self.print_warning(f"Could not retrieve costs: {str(e)}")
            return {
                "total": 0.0,
                "limit": Config.DAILY_BUDGET_LIMIT,
                "remaining": Config.DAILY_BUDGET_LIMIT,
            }

    def print_summary(self):
        """Print test summary"""
        self.print_header("📊 TEST SUMMARY")

        # Overall statistics
        total_tests = len(self.results)
        successful = sum(1 for r in self.results if r["success"])
        failed = total_tests - successful
        success_rate = (successful / total_tests * 100) if total_tests > 0 else 0

        total_duration = sum(r["duration_seconds"] for r in self.results)
        avg_duration = total_duration / total_tests if total_tests > 0 else 0

        print(f"{Colors.BOLD}Overall Results:{Colors.RESET}")
        print(f"  Total tests: {total_tests}")
        print(f"  {Colors.GREEN}Successful: {successful}{Colors.RESET}")
        print(f"  {Colors.RED}Failed: {failed}{Colors.RESET}")
        print(
            f"  Success rate: {Colors.GREEN if success_rate >= 80 else Colors.YELLOW}{success_rate:.1f}%{Colors.RESET}"
        )
        print(f"  Total duration: {total_duration:.2f}s")
        print(f"  Average duration: {avg_duration:.2f}s")

        # Tool-specific results
        self.print_section("🔧 Tool-Specific Results")

        tool_stats = {}
        for result in self.results:
            tool = result["expected_tool"]
            if tool not in tool_stats:
                tool_stats[tool] = {"total": 0, "success": 0, "failed": 0}

            tool_stats[tool]["total"] += 1
            if result["success"]:
                tool_stats[tool]["success"] += 1
            else:
                tool_stats[tool]["failed"] += 1

        for tool, stats in tool_stats.items():
            success_rate = (
                (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
            )
            color = (
                Colors.GREEN
                if success_rate >= 80
                else Colors.YELLOW if success_rate >= 50 else Colors.RED
            )

            print(f"\n{Colors.BOLD}{tool}:{Colors.RESET}")
            print(f"  Tests: {stats['total']}")
            print(f"  {Colors.GREEN}Success: {stats['success']}{Colors.RESET}")
            print(f"  {Colors.RED}Failed: {stats['failed']}{Colors.RESET}")
            print(f"  Rate: {color}{success_rate:.1f}%{Colors.RESET}")

        # Failed tests details
        failed_tests = [r for r in self.results if not r["success"]]
        if failed_tests:
            self.print_section("❌ Failed Tests Details")
            for test in failed_tests:
                print(
                    f"\n{Colors.RED}Test {test['index']}: {test['description']}{Colors.RESET}"
                )
                print(f"  Query: {test['query']}")
                print(f"  Error: {test['error']}")

    async def save_results(self):
        """Save test results to file"""
        try:
            results_dir = Config.DATA_DIR / "test_results"
            results_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = results_dir / f"test_results_{timestamp}.json"

            output = {
                "timestamp": datetime.now().isoformat(),
                "user_id": self.test_user_id,
                "total_tests": len(self.results),
                "successful": sum(1 for r in self.results if r["success"]),
                "failed": sum(1 for r in self.results if not r["success"]),
                "results": self.results,
            }

            with open(results_file, "w") as f:
                json.dump(output, f, indent=2)

            self.print_success(f"Results saved to: {results_file}")

        except Exception as e:
            self.print_warning(f"Could not save results: {str(e)}")

    async def run(self):
        """Run the complete test suite"""
        self.print_header("🚀 CAPETOWN CONSULTANT - COMPREHENSIVE TEST SUITE")

        print(f"{Colors.BOLD}Test Configuration:{Colors.RESET}")
        print(f"  Test User ID: {self.test_user_id}")
        print(f"  Total Queries: {len(self.test_queries)}")
        print(f"  Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Initialize
        if not await self.initialize_assistant():
            self.print_error("Failed to initialize assistant. Exiting.")
            return

        try:
            # Execute all queries
            self.print_header("🧪 EXECUTING TEST QUERIES")

            for index, test_case in enumerate(self.test_queries):
                result = await self.execute_query(test_case, index)
                self.results.append(result)

                # Small delay between queries
                if index < len(self.test_queries) - 1:
                    await asyncio.sleep(2)

            # Get final costs
            self.print_section("💰 Cost Summary")
            costs = await self.get_cost_summary()
            print(f"  Total cost: ${costs.get('total', 0.0):.4f}")
            print(f"  Remaining budget: ${costs.get('remaining', 0.0):.4f}")
            print(
                f"  Budget limit: ${costs.get('limit', Config.DAILY_BUDGET_LIMIT):.2f}"
            )

            # Print summary
            self.print_summary()

            # Save results
            await self.save_results()

        except KeyboardInterrupt:
            self.print_warning("\n\nTest interrupted by user")

        except Exception as e:
            self.print_error(f"Test suite error: {str(e)}")
            logger.error("test_suite_failed", error=str(e))

        finally:
            # Cleanup
            self.print_section("🧹 Cleanup")
            await self.cleanup_assistant()

            self.print_header("✅ TEST SUITE COMPLETED")


async def main():
    """Main entry point"""
    runner = TestRunner()
    await runner.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Interrupted by user{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.RED}Fatal error: {str(e)}{Colors.RESET}")
        sys.exit(1)
