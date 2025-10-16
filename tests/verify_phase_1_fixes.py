#!/usr/bin/env python3
"""
Quick Verification Script for Phase 1 Fixes
Run this script to verify all critical fixes are working correctly
"""

import sys
import asyncio
from colorama import init, Fore, Style

init(autoreset=True)


def print_header(text):
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{'=' * 70}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{text.center(70)}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{'=' * 70}{Style.RESET_ALL}\n")


def print_test(name, passed, details=""):
    icon = f"{Fore.GREEN}✅" if passed else f"{Fore.RED}❌"
    status = f"{Fore.GREEN}PASS" if passed else f"{Fore.RED}FAIL"
    print(f"{icon} {name:<50} [{status}]{Style.RESET_ALL}")
    if details:
        print(f"   {Fore.YELLOW}↳ {details}{Style.RESET_ALL}")


def print_section(title):
    print(f"\n{Fore.MAGENTA}{Style.BRIGHT}▸ {title}{Style.RESET_ALL}")


async def verify_imports():
    """Test 1: Verify all imports work"""
    print_section("Checking Imports")

    tests = []

    # Test schemas import
    try:
        from src.tools.schemas import ToolSchemas
        tests.append(("schemas.py import", True, ""))
    except Exception as e:
        tests.append(("schemas.py import", False, str(e)))

    # Test executor import
    try:
        from src.tools.executor import ToolExecutor
        tests.append(("executor.py import", True, ""))
    except Exception as e:
        tests.append(("executor.py import", False, str(e)))

    # Test embeddings import
    try:
        from src.services.embeddings import EmbeddingService
        tests.append(("embeddings.py import", True, ""))
    except Exception as e:
        tests.append(("embeddings.py import", False, str(e)))

    # Test google search import
    try:
        from src.services.search.google import GoogleSearch
        tests.append(("google.py import", True, ""))
    except Exception as e:
        tests.append(("google.py import", False, str(e)))

    for name, passed, details in tests:
        print_test(name, passed, details)

    return all(passed for _, passed, _ in tests)


async def verify_memory_upsert_schema():
    """Test 2: Verify memory_upsert schema fix"""
    print_section("Memory Upsert Schema")

    from src.tools.schemas import ToolSchemas

    tests = []

    # Check SCHEMAS dict
    schema = ToolSchemas.SCHEMAS.get("memory_upsert", {})
    required = schema.get("required", [])

    test1 = "items" in required and len(required) == 1
    tests.append(("Schema requires only 'items'", test1,
                  f"Required: {required}"))

    # Check function definitions
    defs = ToolSchemas.get_function_definitions()
    memory_def = next(
        (d for d in defs if d["function"]["name"] == "memory_upsert"),
        None
    )

    if memory_def:
        item_schema = memory_def["function"]["parameters"]["properties"]["items"]["items"]
        item_required = item_schema.get("required", [])

        test2 = item_required == ["text"]
        tests.append(("Function def requires only 'text'", test2,
                      f"Item required: {item_required}"))

        test3 = "meta" in item_schema["properties"]
        tests.append(("Function def has 'meta' field", test3, ""))
    else:
        tests.append(("Function definition exists", False, "Not found"))

    # Test validation
    from src.tools.executor import ToolExecutor
    executor = ToolExecutor()

    # Valid case: text only
    valid, error = executor.validate_tool_call(
        "memory_upsert",
        {"items": [{"text": "Test memory"}]}
    )
    tests.append(("Validates text-only items", valid, error or ""))

    # Valid case: text + meta
    valid, error = executor.validate_tool_call(
        "memory_upsert",
        {"items": [{"text": "Test", "meta": {"cat": "test"}}]}
    )
    tests.append(("Validates text + meta items", valid, error or ""))

    # Invalid case: missing text
    valid, error = executor.validate_tool_call(
        "memory_upsert",
        {"items": [{"meta": {"test": "value"}}]}
    )
    tests.append(("Rejects missing text", not valid,
                  "Correctly rejected" if not valid else "Should have failed"))

    for name, passed, details in tests:
        print_test(name, passed, details)

    return all(passed for _, passed, _ in tests)


async def verify_profile_read_schema():
    """Test 3: Verify profile_read schema fix"""
    print_section("Profile Read Schema")

    from src.tools.schemas import ToolSchemas
    from src.tools.executor import ToolExecutor

    tests = []

    # Check SCHEMAS dict
    schema = ToolSchemas.SCHEMAS.get("profile_read", {})
    required = schema.get("required", [])
    optional = schema.get("optional", {})

    test1 = len(required) == 0
    tests.append(("Schema has no required params", test1,
                  f"Required: {required}"))

    test2 = "keys" in optional
    tests.append(("Schema has optional 'keys'", test2, ""))

    # Check function definition
    defs = ToolSchemas.get_function_definitions()
    profile_def = next(
        (d for d in defs if d["function"]["name"] == "profile_read"),
        None
    )

    if profile_def:
        params_required = profile_def["function"]["parameters"].get("required", [])
        test3 = len(params_required) == 0
        tests.append(("Function def has no required params", test3,
                      f"Required: {params_required}"))
    else:
        tests.append(("Function definition exists", False, "Not found"))

    # Test validation
    executor = ToolExecutor()

    # Valid: no parameters
    valid, error = executor.validate_tool_call("profile_read", {})
    tests.append(("Validates empty params (full profile)", valid, error or ""))

    # Valid: with keys
    valid, error = executor.validate_tool_call(
        "profile_read",
        {"keys": ["name", "role"]}
    )
    tests.append(("Validates with keys", valid, error or ""))

    for name, passed, details in tests:
        print_test(name, passed, details)

    return all(passed for _, passed, _ in tests)


async def verify_event_loop_safety():
    """Test 4: Verify event loop safety in rate limiters"""
    print_section("Event Loop Safety")

    from src.services.embeddings import EmbeddingService
    from src.services.search.google import GoogleSearch

    tests = []

    # Test EmbeddingService
    try:
        service = EmbeddingService(api_key="test-key")

        # Check attributes exist
        test1 = hasattr(service, '_rate_limiter')
        test2 = hasattr(service, '_rate_limiter_loop')
        tests.append(("EmbeddingService has limiter attributes",
                      test1 and test2, ""))

        # Get rate limiter
        limiter1 = service.rate_limiter
        test3 = limiter1 is not None
        tests.append(("EmbeddingService creates rate limiter", test3, ""))

        # Get again (should be same in same loop)
        limiter2 = service.rate_limiter
        test4 = limiter1 is limiter2
        tests.append(("EmbeddingService reuses limiter in same loop", test4, ""))

    except Exception as e:
        tests.append(("EmbeddingService rate limiter", False, str(e)))

    # Test GoogleSearch
    try:
        from src.services.cost_tracker import CostTracker
        google = GoogleSearch(cost_tracker=CostTracker())

        test5 = hasattr(google, '_rate_limiter')
        test6 = hasattr(google, '_rate_limiter_loop')
        tests.append(("GoogleSearch has limiter attributes",
                      test5 and test6, ""))

        limiter = google.rate_limiter
        test7 = limiter is not None
        tests.append(("GoogleSearch creates rate limiter", test7, ""))

    except Exception as e:
        tests.append(("GoogleSearch rate limiter", False, str(e)))

    for name, passed, details in tests:
        print_test(name, passed, details)

    return all(passed for _, passed, _ in tests)


async def verify_integration():
    """Test 5: Basic integration test"""
    print_section("Integration Tests")

    tests = []

    # Test profile manager with optional keys
    try:
        import tempfile
        from src.memory.profile import ProfileManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProfileManager(storage_dir=tmpdir)

            # Write profile
            await manager.write("test_user", {
                "name": "Test User",
                "role": "chef"
            })

            # Read full profile (keys=None)
            full = await manager.read("test_user", keys=None)
            test1 = len(full) == 2 and "name" in full
            tests.append(("ProfileManager reads full profile", test1, ""))

            # Read specific keys
            partial = await manager.read("test_user", keys=["name"])
            test2 = len(partial) == 1 and partial.get("name") == "Test User"
            tests.append(("ProfileManager reads specific keys", test2, ""))

    except Exception as e:
        tests.append(("ProfileManager integration", False, str(e)))

    # Test tool executor initialization
    try:
        from src.tools.executor import ToolExecutor

        executor = ToolExecutor()
        test3 = executor is not None
        tests.append(("ToolExecutor initialization", test3, ""))

    except Exception as e:
        tests.append(("ToolExecutor initialization", False, str(e)))

    for name, passed, details in tests:
        print_test(name, passed, details)

    return all(passed for _, passed, _ in tests)


async def main():
    """Run all verification tests"""
    print_header("PHASE 1 FIXES VERIFICATION")

    print(f"{Fore.YELLOW}This script verifies that all Phase 1 critical fixes are working.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}It does not require API keys or external services.{Style.RESET_ALL}")

    results = []

    # Run all verification tests
    results.append(("Imports", await verify_imports()))
    results.append(("Memory Upsert Schema", await verify_memory_upsert_schema()))
    results.append(("Profile Read Schema", await verify_profile_read_schema()))
    results.append(("Event Loop Safety", await verify_event_loop_safety()))
    results.append(("Integration", await verify_integration()))

    # Summary
    print_header("SUMMARY")

    all_passed = all(passed for _, passed in results)

    for name, passed in results:
        icon = f"{Fore.GREEN}✅" if passed else f"{Fore.RED}❌"
        status = f"{Fore.GREEN}PASS" if passed else f"{Fore.RED}FAIL"
        print(f"{icon} {name:<50} [{status}]{Style.RESET_ALL}")

    print()

    if all_passed:
        print(f"{Fore.GREEN}{Style.BRIGHT}🎉 ALL TESTS PASSED!{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Phase 1 fixes are working correctly.{Style.RESET_ALL}")
        print()
        print(f"{Fore.CYAN}Next steps:{Style.RESET_ALL}")
        print(f"  1. Run full test suite: pytest tests/test_phase1_fixes.py -v")
        print(f"  2. Test with CLI: python main.py")
        print(f"  3. Test with Streamlit: streamlit run streamlit_app.py")
        return 0
    else:
        print(f"{Fore.RED}{Style.BRIGHT}⚠️  SOME TESTS FAILED{Style.RESET_ALL}")
        print(f"{Fore.RED}Please review the failures above and ensure files are updated correctly.{Style.RESET_ALL}")
        print()
        print(f"{Fore.CYAN}Troubleshooting:{Style.RESET_ALL}")
        print(f"  1. Verify all files are updated from the artifacts")
        print(f"  2. Check for syntax errors in updated files")
        print(f"  3. Ensure you're in the project root directory")
        print(f"  4. Run: export PYTHONPATH=\"${{PYTHONPATH}}:$(pwd)\"")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Verification cancelled by user.{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}Verification failed with error:{Style.RESET_ALL}")
        print(f"{Fore.RED}{e}{Style.RESET_ALL}")
        import traceback

        traceback.print_exc()
        sys.exit(1)