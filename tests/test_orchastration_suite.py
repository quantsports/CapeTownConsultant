"""
Comprehensive test suite for orchestration system
Validates all integration points and functionality
"""

import asyncio
import sys
from typing import List
from src.interface.assistant import AutonomousAssistant
from src.workers.templates import WorkerType, WorkerTemplates


class OrchestrationTester:
    """Test harness for orchestration system"""

    def __init__(self):
        self.test_results = []
        self.user_id = "test_user"

    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log a test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {test_name}")
        if details:
            print(f"         {details}")
        self.test_results.append((test_name, passed, details))

    async def test_initialization(self):
        """Test 1: Orchestration initialization"""
        print("\n" + "=" * 70)
        print("TEST 1: Initialization")
        print("=" * 70)

        try:
            async with AutonomousAssistant(enable_orchestration=True) as assistant:
                has_orchestrator = assistant.agent.orchestrator is not None
                self.log_test(
                    "Orchestrator initialization",
                    has_orchestrator,
                    f"Orchestrator object: {type(assistant.agent.orchestrator).__name__ if has_orchestrator else 'None'}"
                )

                is_enabled = assistant.get_orchestration_status()
                self.log_test(
                    "Orchestration enabled by default",
                    is_enabled,
                    f"Status: {is_enabled}"
                )

            # Test disabled mode
            async with AutonomousAssistant(enable_orchestration=False) as assistant:
                is_disabled = not assistant.get_orchestration_status()
                self.log_test(
                    "Orchestration can be disabled",
                    is_disabled,
                    f"Status: {not is_disabled}"
                )

        except Exception as e:
            self.log_test("Initialization", False, f"Exception: {str(e)}")

    async def test_toggle_functionality(self):
        """Test 2: Toggle functionality"""
        print("\n" + "=" * 70)
        print("TEST 2: Toggle Functionality")
        print("=" * 70)

        try:
            async with AutonomousAssistant(enable_orchestration=True) as assistant:
                initial = assistant.get_orchestration_status()
                self.log_test("Initial state", initial, f"Enabled: {initial}")

                # Toggle off
                assistant.toggle_orchestration(False)
                after_disable = assistant.get_orchestration_status()
                self.log_test(
                    "Toggle to disabled",
                    not after_disable,
                    f"After toggle: {after_disable}"
                )

                # Toggle on
                assistant.toggle_orchestration(True)
                after_enable = assistant.get_orchestration_status()
                self.log_test(
                    "Toggle to enabled",
                    after_enable,
                    f"After toggle: {after_enable}"
                )

        except Exception as e:
            self.log_test("Toggle functionality", False, f"Exception: {str(e)}")

    async def test_decision_logic(self):
        """Test 3: Orchestration decision logic"""
        print("\n" + "=" * 70)
        print("TEST 3: Decision Logic")
        print("=" * 70)

        test_cases = [
            # (query, should_orchestrate, reason)
            ("Hello", False, "Simple greeting"),
            ("What's 2+2?", False, "Simple question"),
            (
                "Design a comprehensive menu plan with cost analysis and marketing strategy for a new Italian restaurant",
                True,
                "Long complex query with multiple domains"
            ),
            (
                "How can I improve my restaurant operations and train my staff better?",
                True,
                "Multiple questions, action keywords"
            ),
            (
                "analyze my menu costs and recommend pricing strategy",
                True,
                "Multiple action keywords"
            ),
        ]

        try:
            async with AutonomousAssistant(enable_orchestration=True) as assistant:
                agent = assistant.agent

                for query, expected, reason in test_cases:
                    result = agent._should_use_orchestration(query)
                    self.log_test(
                        f"Decision: {query[:50]}...",
                        result == expected,
                        f"Expected: {expected}, Got: {result} | {reason}"
                    )

        except Exception as e:
            self.log_test("Decision logic", False, f"Exception: {str(e)}")

    async def test_worker_selection(self):
        """Test 4: Worker selection"""
        print("\n" + "=" * 70)
        print("TEST 4: Worker Selection")
        print("=" * 70)

        test_queries = [
            ("design a summer menu", [WorkerType.MENU_PLANNER]),
            ("calculate food costs", [WorkerType.COST_ANALYST]),
            ("menu and pricing strategy", [WorkerType.MENU_PLANNER, WorkerType.COST_ANALYST]),
            ("marketing campaign", [WorkerType.MARKETING_STRATEGIST]),
        ]

        for query, expected_workers in test_queries:
            recommended = WorkerTemplates.recommend_workers(query, max_workers=3)

            # Check if expected workers are in recommended
            found = all(w in recommended for w in expected_workers)

            self.log_test(
                f"Selection: {query}",
                found,
                f"Expected: {[w.value for w in expected_workers]}, Got: {[w.value for w in recommended[:len(expected_workers)]]}"
            )

    async def test_simple_orchestration(self):
        """Test 5: Simple orchestration execution"""
        print("\n" + "=" * 70)
        print("TEST 5: Simple Orchestration Execution")
        print("=" * 70)

        # Use a query that should trigger orchestration
        test_query = "Create a quick menu plan with 3 appetizers for a casual restaurant"

        try:
            async with AutonomousAssistant(enable_orchestration=True) as assistant:
                print(f"\nExecuting: {test_query}")
                print("This may take 30-60 seconds...\n")

                response = await assistant.chat(test_query, self.user_id)

                # Check response quality
                has_content = len(response) > 100
                has_orchestration_marker = "🎭" in response or "Multi-Agent" in response
                has_recommendations = any(word in response.lower() for word in ['recommend', 'suggest', 'consider'])

                self.log_test(
                    "Orchestration executed",
                    has_content,
                    f"Response length: {len(response)} chars"
                )

                self.log_test(
                    "Contains orchestration markers",
                    has_orchestration_marker,
                    "Orchestration metadata present"
                )

                self.log_test(
                    "Contains recommendations",
                    has_recommendations,
                    "Response has actionable content"
                )

                print(f"\n{'=' * 70}")
                print("RESPONSE PREVIEW:")
                print("=" * 70)
                print(response[:500] + "..." if len(response) > 500 else response)
                print("=" * 70)

        except Exception as e:
            self.log_test("Orchestration execution", False, f"Exception: {str(e)}")

    async def test_fallback_to_traditional(self):
        """Test 6: Fallback to traditional mode"""
        print("\n" + "=" * 70)
        print("TEST 6: Fallback to Traditional Mode")
        print("=" * 70)

        simple_query = "What is basil?"

        try:
            async with AutonomousAssistant(enable_orchestration=True) as assistant:
                print(f"\nExecuting simple query: {simple_query}")

                response = await assistant.chat(simple_query, self.user_id)

                # Simple queries should NOT have orchestration markers
                is_traditional = "🎭" not in response and "Multi-Agent" not in response
                has_answer = len(response) > 20

                self.log_test(
                    "Uses traditional mode for simple query",
                    is_traditional,
                    "No orchestration markers in response"
                )

                self.log_test(
                    "Provides valid answer",
                    has_answer,
                    f"Response length: {len(response)} chars"
                )

        except Exception as e:
            self.log_test("Fallback mode", False, f"Exception: {str(e)}")

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        total = len(self.test_results)
        passed = sum(1 for _, p, _ in self.test_results if p)
        failed = total - passed

        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Success Rate: {(passed / total * 100):.1f}%")

        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for name, passed, details in self.test_results:
                if not passed:
                    print(f"  - {name}")
                    if details:
                        print(f"    {details}")

        print("\n" + "=" * 70)

        return failed == 0


async def run_all_tests():
    """Run complete test suite"""
    print("\n🧪 ORCHESTRATION SYSTEM TEST SUITE")
    print("=" * 70)
    print("Testing all integration points and functionality")
    print("=" * 70)

    tester = OrchestrationTester()

    # Run all tests
    await tester.test_initialization()
    await tester.test_toggle_functionality()
    await tester.test_decision_logic()
    await tester.test_worker_selection()

    # Optional: Skip expensive tests if not needed
    print("\n⚠️  Note: Tests 5 & 6 make actual API calls and may take time.")
    response = input("Run full orchestration tests? (y/n): ")

    if response.lower() == 'y':
        await tester.test_simple_orchestration()
        await tester.test_fallback_to_traditional()
    else:
        print("Skipping API-based tests")

    # Print summary
    all_passed = tester.print_summary()

    return 0 if all_passed else 1


async def interactive_demo():
    """Interactive demonstration of orchestration"""
    print("\n🎭 INTERACTIVE ORCHESTRATION DEMO")
    print("=" * 70)

    test_queries = [
        "Design a spring menu with seasonal ingredients",
        "Analyze food costs and suggest pricing strategy",
        "Create a comprehensive restaurant opening plan including menu, costs, and marketing",
    ]

    print("\nSample queries to try:")
    for i, query in enumerate(test_queries, 1):
        print(f"{i}. {query}")

    print("\nOr enter your own query (or 'quit' to exit)")

    async with AutonomousAssistant(enable_orchestration=True) as assistant:
        while True:
            query = input("\n🎭 Query: ").strip()

            if query.lower() in ['quit', 'exit', 'q']:
                break

            if not query:
                continue

            # Check if it's a number (sample query selection)
            if query.isdigit() and 1 <= int(query) <= len(test_queries):
                query = test_queries[int(query) - 1]
                print(f"Using: {query}")

            print(f"\n{'=' * 70}")
            response = await assistant.chat(query, "demo_user")
            print(f"\n{response}")
            print(f"{'=' * 70}")


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()

        if mode == 'test':
            exit_code = asyncio.run(run_all_tests())
            sys.exit(exit_code)
        elif mode == 'demo':
            asyncio.run(interactive_demo())
        else:
            print("Usage:")
            print("  python test_orchestration.py test  - Run test suite")
            print("  python test_orchestration.py demo  - Interactive demo")
    else:
        # Default: run tests
        exit_code = asyncio.run(run_all_tests())
        sys.exit(exit_code)


if __name__ == "__main__":
    main()