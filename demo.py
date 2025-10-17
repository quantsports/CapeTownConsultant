"""
Advanced Demo for CapeTownConsultant
Simulates complex multi-agent orchestration, concurrent operations, and performance testing
"""

import asyncio
import sys
import statistics
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
import json
import time

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.interface.assistant import AutonomousAssistant
from src.services.cost_tracker import CostTracker
from src.config.settings import Config
from src.core.logging import logger
from src.workers.templates import WorkerType


# Terminal colors
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


@dataclass
class QueryResult:
    """Enhanced result tracking"""
    query: str
    description: str
    user_id: str
    start_time: float
    end_time: float = 0.0
    duration: float = 0.0
    success: bool = False
    response: Optional[str] = None
    error: Optional[str] = None
    tokens_used: int = 0
    cost: float = 0.0
    worker_types: List[str] = field(default_factory=list)
    orchestration_enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkMetrics:
    """Performance metrics"""
    total_queries: int = 0
    successful: int = 0
    failed: int = 0
    total_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    avg_duration: float = 0.0
    median_duration: float = 0.0
    p95_duration: float = 0.0
    p99_duration: float = 0.0
    total_cost: float = 0.0
    queries_per_second: float = 0.0


class AdvancedTestRunner:
    """Enhanced test runner with orchestration and concurrency support"""

    def __init__(self, enable_orchestration: bool = True, concurrency_level: int = 1):
        self.test_user_id = f"demo_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.results: List[QueryResult] = []
        self.assistant: Optional[AutonomousAssistant] = None
        self.cost_tracker: Optional[CostTracker] = None
        self.enable_orchestration = enable_orchestration
        self.concurrency_level = concurrency_level
        self.progress_messages: List[str] = []

        # Complex test scenarios
        self.test_scenarios = [
            {
                "query": "Store in memory: I'm a restaurant owner in Cape Town, budget is $250k, prefer Italian cuisine",
                "description": "Complex memory storage - multiple data points",
                "category": "memory",
                "expected_workers": None,
            },
            {
                "query": "What are the latest restaurant industry trends in South Africa for 2024-2025?",
                "description": "Web search with time-sensitive requirements",
                "category": "search",
                "expected_workers": [WorkerType.RESEARCH_ANALYST],
            },
            {
                "query": "Analyze the competitive landscape for Italian restaurants in Cape Town",
                "description": "Multi-source research requiring synthesis",
                "category": "analysis",
                "expected_workers": [WorkerType.RESEARCH_ANALYST, WorkerType.BUSINESS_ANALYST],
            },
            {
                "query": "What are my stored preferences and budget?",
                "description": "Memory retrieval - multi-field query",
                "category": "memory",
                "expected_workers": None,
            },
            {
                "query": "Provide a comprehensive market analysis for opening a sustainable farm-to-table restaurant",
                "description": "Complex orchestration - multiple workers needed",
                "category": "complex",
                "expected_workers": [WorkerType.RESEARCH_ANALYST, WorkerType.BUSINESS_ANALYST, WorkerType.DATA_SYNTHESIZER],
            },
            {
                "query": "Compare the cost of restaurant licenses in Cape Town vs Johannesburg",
                "description": "Comparative research query",
                "category": "comparison",
                "expected_workers": [WorkerType.RESEARCH_ANALYST],
            },
            {
                "query": "Remember: I want to incorporate wine pairings and have sommelier expertise",
                "description": "Additional memory storage - specialty info",
                "category": "memory",
                "expected_workers": None,
            },
            {
                "query": "What regulatory requirements exist for restaurants serving alcohol in Western Cape?",
                "description": "Regulatory/legal research",
                "category": "regulatory",
                "expected_workers": [WorkerType.RESEARCH_ANALYST],
            },
            {
                "query": "Create a strategic plan for my restaurant concept based on everything you know about my preferences",
                "description": "Memory recall + strategic synthesis",
                "category": "complex",
                "expected_workers": [WorkerType.BUSINESS_ANALYST, WorkerType.DATA_SYNTHESIZER],
            },
            {
                "query": "What are the pros and cons of ghost kitchens vs traditional restaurant models in South Africa?",
                "description": "Analytical comparison requiring deep research",
                "category": "analysis",
                "expected_workers": [WorkerType.RESEARCH_ANALYST, WorkerType.CRITICAL_EVALUATOR],
            },
        ]

    def print_header(self, text: str):
        """Print formatted header"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 100}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.HEADER}{text.center(100)}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 100}{Colors.RESET}\n")

    def print_section(self, text: str):
        """Print formatted section"""
        print(f"\n{Colors.CYAN}{Colors.BOLD}{text}{Colors.RESET}")
        print(f"{Colors.CYAN}{'-' * 100}{Colors.RESET}")

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

    def progress_callback(self, message: str):
        """Callback for progress updates"""
        self.progress_messages.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        print(f"{Colors.MAGENTA}  → {message}{Colors.RESET}")

    async def initialize_assistant(self) -> bool:
        """Initialize assistant with orchestration support"""
        self.print_section("🔧 Initializing Advanced Assistant")

        try:
            # Validate configuration
            if not Config.OPENAI_API_KEY:
                self.print_error("OPENAI_API_KEY not configured")
                return False

            self.print_success("OpenAI API key found")

            # Check optional APIs
            optional_apis = {
                "Pinecone": Config.PINECONE_API_KEY,
                "SerpAPI": Config.SERPAPI_API_KEY,
                "Perplexity": Config.PERPLEXITY_API_KEY,
            }

            for name, key in optional_apis.items():
                if key:
                    self.print_success(f"{name} configured")
                else:
                    self.print_warning(f"{name} not configured (optional)")

            # Initialize cost tracker
            self.cost_tracker = CostTracker()
            self.print_success("Cost tracker initialized")

            # Initialize assistant with orchestration
            self.print_info(f"Initializing assistant (orchestration: {self.enable_orchestration})...")
            self.assistant = await AutonomousAssistant(
                cost_tracker=self.cost_tracker,
                enable_orchestration=self.enable_orchestration
            ).__aenter__()

            # Set progress callback
            self.assistant.set_progress_callback(self.progress_callback)

            self.print_success("Assistant initialized with progress tracking")
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

    async def execute_single_query(
        self, scenario: Dict[str, Any], index: int, total: int
    ) -> QueryResult:
        """Execute a single test query with detailed tracking"""
        query = scenario["query"]
        description = scenario["description"]
        category = scenario["category"]

        self.print_section(f"Test {index + 1}/{total}: {description}")
        self.print_info(f"Query: {query}")
        self.print_info(f"Category: {category}")
        self.print_info(f"Orchestration: {'Enabled' if self.enable_orchestration else 'Disabled'}")

        start_time = time.time()
        result = QueryResult(
            query=query,
            description=description,
            user_id=self.test_user_id,
            start_time=start_time,
            orchestration_enabled=self.enable_orchestration,
            metadata={"category": category, "index": index}
        )

        # Clear progress messages for this query
        self.progress_messages = []

        try:
            # Execute query with timeout
            response = await asyncio.wait_for(
                self.assistant.chat(query, self.test_user_id),
                timeout=180.0
            )

            end_time = time.time()
            duration = end_time - start_time

            result.end_time = end_time
            result.duration = duration
            result.response = response
            result.success = True

            # Check for errors in response
            response_lower = response.lower()
            if "error" in response_lower or "failed" in response_lower:
                result.success = False
                result.error = "Response contains error indicators"
                self.print_error(f"Query failed with errors in response")
            else:
                self.print_success(f"Query completed in {duration:.2f}s")

            # Display response preview
            preview_length = 250
            preview = response[:preview_length] + "..." if len(response) > preview_length else response
            print(f"\n{Colors.CYAN}Response preview:{Colors.RESET}")
            print(f"{preview}\n")

            # Display progress messages
            if self.progress_messages:
                print(f"{Colors.MAGENTA}Progress updates: {len(self.progress_messages)}{Colors.RESET}")

        except asyncio.TimeoutError:
            end_time = time.time()
            duration = end_time - start_time
            result.end_time = end_time
            result.duration = duration
            result.error = "Query timed out after 180 seconds"
            self.print_error("Query timed out")

        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            result.end_time = end_time
            result.duration = duration
            result.error = str(e)
            self.print_error(f"Query failed: {str(e)}")
            logger.error("query_execution_failed", query=query, error=str(e))

        return result

    async def execute_concurrent_queries(
        self, scenarios: List[Dict[str, Any]], batch_name: str
    ) -> List[QueryResult]:
        """Execute multiple queries concurrently"""
        self.print_section(f"🔄 Executing {len(scenarios)} queries concurrently - {batch_name}")

        tasks = []
        for idx, scenario in enumerate(scenarios):
            task = self.execute_single_query(scenario, idx, len(scenarios))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.print_error(f"Concurrent query {i+1} raised exception: {str(result)}")
                error_result = QueryResult(
                    query=scenarios[i]["query"],
                    description=scenarios[i]["description"],
                    user_id=self.test_user_id,
                    start_time=time.time(),
                    end_time=time.time(),
                    error=str(result),
                    orchestration_enabled=self.enable_orchestration
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)

        return processed_results

    async def run_sequential_tests(self):
        """Run tests sequentially"""
        self.print_header("🧪 SEQUENTIAL TEST EXECUTION")

        for index, scenario in enumerate(self.test_scenarios):
            result = await self.execute_single_query(scenario, index, len(self.test_scenarios))
            self.results.append(result)

            # Small delay between queries
            if index < len(self.test_scenarios) - 1:
                await asyncio.sleep(2)

    async def run_concurrent_tests(self):
        """Run tests with controlled concurrency"""
        self.print_header(f"⚡ CONCURRENT TEST EXECUTION (Level: {self.concurrency_level})")

        # Split scenarios into batches
        batch_size = self.concurrency_level
        for i in range(0, len(self.test_scenarios), batch_size):
            batch = self.test_scenarios[i:i + batch_size]
            batch_name = f"Batch {i // batch_size + 1}"

            batch_results = await self.execute_concurrent_queries(batch, batch_name)
            self.results.extend(batch_results)

            # Delay between batches
            if i + batch_size < len(self.test_scenarios):
                self.print_info("Cooling down between batches...")
                await asyncio.sleep(3)

    def calculate_metrics(self) -> BenchmarkMetrics:
        """Calculate comprehensive performance metrics"""
        if not self.results:
            return BenchmarkMetrics()

        successful_results = [r for r in self.results if r.success]
        durations = [r.duration for r in self.results if r.duration > 0]

        metrics = BenchmarkMetrics(
            total_queries=len(self.results),
            successful=len(successful_results),
            failed=len(self.results) - len(successful_results),
            total_duration=sum(durations) if durations else 0.0,
        )

        if durations:
            metrics.min_duration = min(durations)
            metrics.max_duration = max(durations)
            metrics.avg_duration = statistics.mean(durations)
            metrics.median_duration = statistics.median(durations)

            # Calculate percentiles
            sorted_durations = sorted(durations)
            if len(sorted_durations) >= 2:
                p95_idx = int(len(sorted_durations) * 0.95)
                p99_idx = int(len(sorted_durations) * 0.99)
                metrics.p95_duration = sorted_durations[min(p95_idx, len(sorted_durations) - 1)]
                metrics.p99_duration = sorted_durations[min(p99_idx, len(sorted_durations) - 1)]

            # Calculate throughput
            if metrics.total_duration > 0:
                metrics.queries_per_second = len(durations) / metrics.total_duration

        return metrics

    def print_metrics_report(self, metrics: BenchmarkMetrics):
        """Print detailed metrics report"""
        self.print_header("📊 PERFORMANCE METRICS")

        print(f"{Colors.BOLD}Overall Statistics:{Colors.RESET}")
        print(f"  Total queries: {metrics.total_queries}")
        print(f"  {Colors.GREEN}Successful: {metrics.successful}{Colors.RESET}")
        print(f"  {Colors.RED}Failed: {metrics.failed}{Colors.RESET}")
        success_rate = (metrics.successful / metrics.total_queries * 100) if metrics.total_queries > 0 else 0
        color = Colors.GREEN if success_rate >= 80 else Colors.YELLOW if success_rate >= 50 else Colors.RED
        print(f"  Success rate: {color}{success_rate:.1f}%{Colors.RESET}")

        print(f"\n{Colors.BOLD}Timing Analysis:{Colors.RESET}")
        print(f"  Total duration: {metrics.total_duration:.2f}s")
        print(f"  Min duration: {metrics.min_duration:.2f}s")
        print(f"  Max duration: {metrics.max_duration:.2f}s")
        print(f"  Avg duration: {metrics.avg_duration:.2f}s")
        print(f"  Median duration: {metrics.median_duration:.2f}s")
        print(f"  P95 duration: {metrics.p95_duration:.2f}s")
        print(f"  P99 duration: {metrics.p99_duration:.2f}s")

        print(f"\n{Colors.BOLD}Throughput:{Colors.RESET}")
        print(f"  Queries/second: {metrics.queries_per_second:.3f}")

        # Category breakdown
        self.print_section("📑 Category Breakdown")
        category_stats: Dict[str, Dict[str, int]] = {}

        for result in self.results:
            category = result.metadata.get("category", "unknown")
            if category not in category_stats:
                category_stats[category] = {"total": 0, "success": 0, "failed": 0}

            category_stats[category]["total"] += 1
            if result.success:
                category_stats[category]["success"] += 1
            else:
                category_stats[category]["failed"] += 1

        for category, stats in sorted(category_stats.items()):
            rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
            color = Colors.GREEN if rate >= 80 else Colors.YELLOW if rate >= 50 else Colors.RED
            print(f"\n{Colors.BOLD}{category.upper()}:{Colors.RESET}")
            print(f"  Total: {stats['total']} | Success: {stats['success']} | Failed: {stats['failed']}")
            print(f"  Rate: {color}{rate:.1f}%{Colors.RESET}")

    async def get_cost_summary(self) -> Dict[str, float]:
        """Get cost summary"""
        try:
            costs = await self.assistant.get_costs(self.test_user_id)
            return costs
        except Exception as e:
            self.print_warning(f"Could not retrieve costs: {str(e)}")
            return {"total": 0.0, "limit": Config.DAILY_BUDGET_LIMIT, "remaining": Config.DAILY_BUDGET_LIMIT}

    async def save_results(self, metrics: BenchmarkMetrics):
        """Save comprehensive results"""
        try:
            results_dir = Config.DATA_DIR / "demo_results"
            results_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            mode = "orchestrated" if self.enable_orchestration else "traditional"
            results_file = results_dir / f"demo_results_{mode}_{timestamp}.json"

            # Convert results to dict
            results_dict = []
            for r in self.results:
                results_dict.append({
                    "query": r.query,
                    "description": r.description,
                    "duration": r.duration,
                    "success": r.success,
                    "error": r.error,
                    "response_length": len(r.response) if r.response else 0,
                    "orchestration_enabled": r.orchestration_enabled,
                    "metadata": r.metadata,
                })

            output = {
                "timestamp": datetime.now().isoformat(),
                "user_id": self.test_user_id,
                "configuration": {
                    "orchestration_enabled": self.enable_orchestration,
                    "concurrency_level": self.concurrency_level,
                },
                "metrics": {
                    "total_queries": metrics.total_queries,
                    "successful": metrics.successful,
                    "failed": metrics.failed,
                    "avg_duration": metrics.avg_duration,
                    "median_duration": metrics.median_duration,
                    "p95_duration": metrics.p95_duration,
                    "queries_per_second": metrics.queries_per_second,
                },
                "results": results_dict,
            }

            with open(results_file, "w") as f:
                json.dump(output, f, indent=2)

            self.print_success(f"Results saved to: {results_file}")

        except Exception as e:
            self.print_warning(f"Could not save results: {str(e)}")

    async def run(self, mode: str = "sequential"):
        """Run the demo suite"""
        self.print_header("🚀 ADVANCED CAPETOWN CONSULTANT DEMO")

        print(f"{Colors.BOLD}Configuration:{Colors.RESET}")
        print(f"  User ID: {self.test_user_id}")
        print(f"  Total Scenarios: {len(self.test_scenarios)}")
        print(f"  Orchestration: {self.enable_orchestration}")
        print(f"  Mode: {mode}")
        print(f"  Concurrency Level: {self.concurrency_level}")
        print(f"  Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Initialize
        if not await self.initialize_assistant():
            self.print_error("Failed to initialize assistant. Exiting.")
            return

        try:
            # Execute tests based on mode
            if mode == "concurrent":
                await self.run_concurrent_tests()
            else:
                await self.run_sequential_tests()

            # Calculate metrics
            metrics = self.calculate_metrics()

            # Print metrics
            self.print_metrics_report(metrics)

            # Get costs
            self.print_section("💰 Cost Summary")
            costs = await self.get_cost_summary()
            print(f"  Total cost: ${costs.get('total', 0.0):.4f}")
            print(f"  Remaining budget: ${costs.get('remaining', 0.0):.4f}")
            print(f"  Budget limit: ${costs.get('limit', Config.DAILY_BUDGET_LIMIT):.2f}")

            # Save results
            await self.save_results(metrics)

        except KeyboardInterrupt:
            self.print_warning("\n\nDemo interrupted by user")

        except Exception as e:
            self.print_error(f"Demo suite error: {str(e)}")
            logger.error("demo_suite_failed", error=str(e))

        finally:
            # Cleanup
            self.print_section("🧹 Cleanup")
            await self.cleanup_assistant()

            self.print_header("✅ DEMO SUITE COMPLETED")


async def main():
    """Main entry point with mode selection"""
    print(f"{Colors.BOLD}{Colors.CYAN}CapeTown Consultant - Advanced Demo{Colors.RESET}\n")
    print("Available modes:")
    print("  1. Sequential (default) - Run tests one by one")
    print("  2. Concurrent - Run tests in parallel batches")
    print("  3. Comparison - Run both modes for comparison")
    print()

    # Configuration
    mode_input = input("Select mode (1/2/3) [1]: ").strip() or "1"

    orchestration_input = input("Enable orchestration? (y/n) [y]: ").strip().lower() or "y"
    enable_orchestration = orchestration_input == "y"

    concurrency_input = input("Concurrency level (1-5) [2]: ").strip() or "2"
    try:
        concurrency_level = max(1, min(5, int(concurrency_input)))
    except ValueError:
        concurrency_level = 2

    if mode_input == "3":
        # Comparison mode
        print(f"\n{Colors.BOLD}Running comparison mode...{Colors.RESET}\n")

        # Run sequential
        print(f"{Colors.CYAN}{'=' * 100}{Colors.RESET}")
        print(f"{Colors.CYAN}PHASE 1: SEQUENTIAL MODE{Colors.RESET}")
        print(f"{Colors.CYAN}{'=' * 100}{Colors.RESET}")
        runner1 = AdvancedTestRunner(
            enable_orchestration=enable_orchestration,
            concurrency_level=1
        )
        await runner1.run(mode="sequential")

        # Wait between runs
        print(f"\n{Colors.YELLOW}Waiting 10 seconds before concurrent run...{Colors.RESET}")
        await asyncio.sleep(10)

        # Run concurrent
        print(f"\n{Colors.CYAN}{'=' * 100}{Colors.RESET}")
        print(f"{Colors.CYAN}PHASE 2: CONCURRENT MODE{Colors.RESET}")
        print(f"{Colors.CYAN}{'=' * 100}{Colors.RESET}")
        runner2 = AdvancedTestRunner(
            enable_orchestration=enable_orchestration,
            concurrency_level=concurrency_level
        )
        await runner2.run(mode="concurrent")

        # Print comparison
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 100}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'COMPARISON SUMMARY'.center(100)}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 100}{Colors.RESET}\n")

        metrics1 = runner1.calculate_metrics()
        metrics2 = runner2.calculate_metrics()

        print(f"{Colors.BOLD}Sequential vs Concurrent:{Colors.RESET}")
        print(f"  Avg Duration: {metrics1.avg_duration:.2f}s vs {metrics2.avg_duration:.2f}s")
        print(f"  Total Duration: {metrics1.total_duration:.2f}s vs {metrics2.total_duration:.2f}s")
        print(f"  Success Rate: {(metrics1.successful/metrics1.total_queries*100):.1f}% vs {(metrics2.successful/metrics2.total_queries*100):.1f}%")
        print(f"  Throughput: {metrics1.queries_per_second:.3f} vs {metrics2.queries_per_second:.3f} queries/sec")

        speedup = metrics1.total_duration / metrics2.total_duration if metrics2.total_duration > 0 else 0
        print(f"\n  {Colors.GREEN}Speedup: {speedup:.2f}x{Colors.RESET}")

    else:
        # Single mode
        mode_name = "concurrent" if mode_input == "2" else "sequential"
        runner = AdvancedTestRunner(
            enable_orchestration=enable_orchestration,
            concurrency_level=concurrency_level if mode_input == "2" else 1
        )
        await runner.run(mode=mode_name)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Interrupted by user{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.RED}Fatal error: {str(e)}{Colors.RESET}")
        sys.exit(1)
