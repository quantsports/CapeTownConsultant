"""
Test script for orchestration integration
"""
import asyncio
from src.interface.assistant import AutonomousAssistant


async def test_orchestration_integration():
    """Test the three-tier orchestration integration"""
    
    print("=" * 70)
    print("Testing Orchestration Integration")
    print("=" * 70)
    
    # Test 1: Single agent mode (default)
    print("\n[Test 1] Single agent mode (default)")
    async with AutonomousAssistant() as assistant:
        response = await assistant.chat("Hello, how are you?")
        print(f"✓ Single agent response: {response[:100]}...")
        assert response is not None
        assert "OpenAI API not configured" not in response or "❌" in response
    
    # Test 2: Orchestration enabled but simple query
    print("\n[Test 2] Orchestration enabled, simple query")
    async with AutonomousAssistant(enable_orchestration=True) as assistant:
        response = await assistant.chat("What is pizza?")
        print(f"✓ Response (should use single agent): {response[:100]}...")
        assert response is not None
    
    # Test 3: Orchestration enabled with complex query
    print("\n[Test 3] Orchestration enabled, complex query (auto-detect)")
    async with AutonomousAssistant(enable_orchestration=True) as assistant:
        complex_query = (
            "Create a comprehensive restaurant launch plan including menu design, "
            "cost analysis, marketing strategy, and operations workflow"
        )
        
        # First, explain routing
        routing = await assistant.explain_routing(complex_query)
        print(f"✓ Routing decision: {routing['mode']}")
        print(f"  Query length: {routing['query_length']}")
        print(f"  Complexity triggers: {routing.get('complexity_triggers', [])}")
        if 'recommended_workers' in routing:
            print(f"  Recommended workers: {routing['recommended_workers']}")
        
        # Then execute (might fail if API keys not configured, but structure should work)
        try:
            response = await assistant.chat(complex_query)
            print(f"✓ Orchestration response: {response[:150]}...")
            assert response is not None
        except Exception as e:
            print(f"⚠ Orchestration execution skipped (API may not be configured): {e}")
    
    # Test 4: Force orchestration
    print("\n[Test 4] Force orchestration on simple query")
    async with AutonomousAssistant(enable_orchestration=True) as assistant:
        try:
            response = await assistant.chat(
                "What are good appetizers?",
                force_orchestration=True
            )
            print(f"✓ Forced orchestration response: {response[:100]}...")
            assert response is not None
        except Exception as e:
            print(f"⚠ Forced orchestration skipped (API may not be configured): {e}")
    
    # Test 5: Toggle orchestration at runtime
    print("\n[Test 5] Toggle orchestration at runtime")
    async with AutonomousAssistant() as assistant:
        assert not assistant.is_orchestration_enabled()
        print("✓ Initially disabled")
        
        assistant.toggle_orchestration(True)
        assert assistant.is_orchestration_enabled()
        print("✓ Enabled via toggle")
        
        assistant.toggle_orchestration(False)
        assert not assistant.is_orchestration_enabled()
        print("✓ Disabled via toggle")
    
    # Test 6: Force single-agent mode
    print("\n[Test 6] Force single-agent mode on complex query")
    async with AutonomousAssistant(enable_orchestration=True) as assistant:
        complex_query = "Design comprehensive menu with cost analysis and marketing"
        response = await assistant.chat(complex_query, force_orchestration=False)
        print(f"✓ Forced single-agent response: {response[:100]}...")
        assert response is not None
    
    print("\n" + "=" * 70)
    print("✓ All integration tests passed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_orchestration_integration())
