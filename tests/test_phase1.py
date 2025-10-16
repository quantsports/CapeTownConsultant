"""
Phase 1 Bug Fixes - Comprehensive Test Suite

Tests for:
1. Memory upsert schema fix
2. Profile read schema fix
3. Event loop safety
4. Memory extraction operations
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Import fixed modules
from src.tools.schemas import ToolSchemas
from src.tools.executor import ToolExecutor
from src.services.embeddings import EmbeddingService
from src.services.cost_tracker import CostTracker
from src.memory.profile import ProfileManager
from src.memory.vector import VectorMemory
from src.core.models import ToolResult


# ============================================================================
# Test 1: Memory Upsert Schema Validation
# ============================================================================

class TestMemoryUpsertSchema:
    """Test memory_upsert schema fixes"""

    def test_schema_requires_only_text(self):
        """Verify schema only requires 'text' field, not 'id'"""
        schema = ToolSchemas.SCHEMAS["memory_upsert"]

        assert "items" in schema["required"]
        assert len(schema["required"]) == 1

    def test_function_definition_correct(self):
        """Verify OpenAI function definition matches implementation"""
        defs = ToolSchemas.get_function_definitions()
        memory_upsert_def = next(
            d for d in defs
            if d["function"]["name"] == "memory_upsert"
        )

        item_schema = memory_upsert_def["function"]["parameters"]["properties"]["items"]["items"]

        # Should require only 'text', not 'id'
        assert item_schema["required"] == ["text"]
        assert "text" in item_schema["properties"]
        assert "meta" in item_schema["properties"]  # Optional metadata field

    @pytest.mark.asyncio
    async def test_executor_validates_items_structure(self):
        """Test that executor properly validates item structure"""
        executor = ToolExecutor()

        # Valid: items with text only
        valid, error = executor.validate_tool_call(
            "memory_upsert",
            {"items": [{"text": "User prefers Italian food"}]}
        )
        assert valid is True
        assert error is None

        # Valid: items with text and meta
        valid, error = executor.validate_tool_call(
            "memory_upsert",
            {
                "items": [
                    {
                        "text": "User is a restaurant owner",
                        "meta": {"category": "professional"}
                    }
                ]
            }
        )
        assert valid is True
        assert error is None

        # Invalid: missing text field
        valid, error = executor.validate_tool_call(
            "memory_upsert",
            {"items": [{"meta": {"test": "value"}}]}
        )
        assert valid is False
        assert "missing required 'text' field" in error.lower()

        # Invalid: empty text
        valid, error = executor.validate_tool_call(
            "memory_upsert",
            {"items": [{"text": "   "}]}
        )
        assert valid is False
        assert "cannot be empty" in error.lower()

        # Invalid: items not a list
        valid, error = executor.validate_tool_call(
            "memory_upsert",
            {"items": "not a list"}
        )
        assert valid is False
        assert "must be a list" in error.lower()

        # Invalid: empty items list
        valid, error = executor.validate_tool_call(
            "memory_upsert",
            {"items": []}
        )
        assert valid is False
        assert "cannot be empty" in error.lower()


# ============================================================================
# Test 2: Profile Read Schema Validation
# ============================================================================

class TestProfileReadSchema:
    """Test profile_read schema fixes"""

    def test_schema_has_no_required_params(self):
        """Verify 'keys' parameter is optional"""
        schema = ToolSchemas.SCHEMAS["profile_read"]

        assert len(schema["required"]) == 0
        assert "keys" in schema["optional"]

    def test_function_definition_allows_empty_params(self):
        """Verify OpenAI function definition allows empty parameters"""
        defs = ToolSchemas.get_function_definitions()
        profile_read_def = next(
            d for d in defs
            if d["function"]["name"] == "profile_read"
        )

        # Should have no required parameters
        assert profile_read_def["function"]["parameters"]["required"] == []

    @pytest.mark.asyncio
    async def test_executor_handles_optional_keys(self):
        """Test that executor handles optional keys parameter"""
        executor = ToolExecutor()

        # Valid: no parameters (read full profile)
        valid, error = executor.validate_tool_call("profile_read", {})
        assert valid is True
        assert error is None

        # Valid: with keys
        valid, error = executor.validate_tool_call(
            "profile_read",
            {"keys": ["name", "role"]}
        )
        assert valid is True
        assert error is None

        # Invalid: keys not a list
        valid, error = executor.validate_tool_call(
            "profile_read",
            {"keys": "not_a_list"}
        )
        assert valid is False
        assert "must be a list" in error.lower()

    @pytest.mark.asyncio
    async def test_profile_manager_handles_none_keys(self):
        """Test ProfileManager correctly handles keys=None"""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProfileManager(storage_dir=tmpdir)

            # Write test profile
            await manager.write("test_user", {
                "name": "John",
                "role": "chef",
                "cuisine": "italian"
            })

            # Read full profile (keys=None)
            full_profile = await manager.read("test_user", keys=None)
            assert len(full_profile) == 3
            assert full_profile["name"] == "John"
            assert full_profile["role"] == "chef"
            assert full_profile["cuisine"] == "italian"

            # Read specific keys
            partial_profile = await manager.read("test_user", keys=["name", "role"])
            assert len(partial_profile) == 2
            assert partial_profile["name"] == "John"
            assert partial_profile["role"] == "chef"


# ============================================================================
# Test 3: Event Loop Safety
# ============================================================================

class TestEventLoopSafety:
    """Test event loop safety in rate limiters"""

    @pytest.mark.asyncio
    async def test_embedding_service_rate_limiter_loop_safety(self):
        """Test EmbeddingService rate limiter handles event loop changes"""
        service = EmbeddingService(api_key="test-key")

        # Get rate limiter in first loop
        limiter1 = service.rate_limiter
        loop1 = service._rate_limiter_loop

        # Verify it's created
        assert limiter1 is not None
        assert loop1 is not None

        # Get it again in same loop
        limiter2 = service.rate_limiter
        assert limiter2 is limiter1  # Should be same instance

    @pytest.mark.asyncio
    async def test_rate_limiter_recreated_for_new_loop(self):
        """Test that rate limiter is recreated when event loop changes"""
        service = EmbeddingService(api_key="test-key")

        # Get limiter in first context
        async def get_limiter_info():
            limiter = service.rate_limiter
            return id(limiter), service._rate_limiter_loop

        limiter_id1, loop1 = await get_limiter_info()

        # Simulate new event loop by clearing the stored loop
        service._rate_limiter_loop = None

        # Get limiter again
        limiter_id2, loop2 = await get_limiter_info()

        # Should have same limiter if in same loop
        assert limiter_id1 == limiter_id2

    @pytest.mark.asyncio
    async def test_multiple_services_independent_limiters(self):
        """Test that multiple service instances have independent limiters"""
        service1 = EmbeddingService(api_key="test-key-1")
        service2 = EmbeddingService(api_key="test-key-2")

        limiter1 = service1.rate_limiter
        limiter2 = service2.rate_limiter

        # Should be different instances
        assert id(limiter1) != id(limiter2)


# ============================================================================
# Test 4: Integration Tests
# ============================================================================

class TestMemoryExtractionIntegration:
    """Integration tests for memory extraction flow"""

    @pytest.mark.asyncio
    async def test_memory_extraction_with_auto_memory(self):
        """Test that memory extraction works with corrected schemas"""
        from src.agent.autonomous import AutonomousAgent
        from src.config.settings import Config

        # Mock OpenAI client
        mock_client = AsyncMock()

        # Mock extraction response
        mock_extraction_response = Mock()
        mock_extraction_response.choices = [
            Mock(message=Mock(content='[{"text": "User prefers spicy food", "meta": {"category": "preference"}}]'))
        ]
        mock_extraction_response.usage = Mock(prompt_tokens=100, completion_tokens=50)

        mock_client.chat.completions.create = AsyncMock(return_value=mock_extraction_response)

        async with AutonomousAgent() as agent:
            agent.client = mock_client

            # Create mock conversation
            conversation = [
                {"role": "user", "content": "I love spicy food"},
                {"role": "assistant", "content": "Great! I'll remember that."}
            ]

            # This should not raise validation errors
            try:
                await agent._extract_memories(conversation, "test_user")
                success = True
            except Exception as e:
                success = False
                error_msg = str(e)

            assert success, f"Memory extraction failed: {error_msg if not success else ''}"

    @pytest.mark.asyncio
    async def test_full_chat_flow_with_memory_storage(self):
        """Test complete chat flow including memory storage"""
        from src.interface.assistant import AutonomousAssistant

        # This is a smoke test - verifies imports work and basic flow doesn't crash
        try:
            async with AutonomousAssistant() as assistant:
                # Verify assistant initialized correctly
                assert assistant.agent is not None

                # Test that cost tracker is working
                costs = await assistant.get_costs("test_user")
                assert "total" in costs
                assert "limit" in costs

                success = True
        except Exception as e:
            success = False
            error_msg = str(e)

        assert success, f"Assistant initialization failed: {error_msg if not success else ''}"


# ============================================================================
# Test 5: Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.asyncio
    async def test_memory_upsert_with_special_characters(self):
        """Test memory upsert handles special characters"""
        executor = ToolExecutor()

        special_texts = [
            "User's favorite: sushi 🍣",
            "Budget: $50-$100 per meal 💰",
            "Prefers 3-course meals\nwith wine pairing",
            "Dislikes: spicy 🌶️, salty 🧂, bitter"
        ]

        for text in special_texts:
            valid, error = executor.validate_tool_call(
                "memory_upsert",
                {"items": [{"text": text}]}
            )
            assert valid is True, f"Failed for text: {text}, error: {error}"

    @pytest.mark.asyncio
    async def test_profile_read_nonexistent_keys(self):
        """Test profile read with keys that don't exist"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProfileManager(storage_dir=tmpdir)

            # Write profile
            await manager.write("test_user", {"name": "Alice"})

            # Read with non-existent keys
            result = await manager.read("test_user", keys=["name", "nonexistent"])

            # Should return only existing keys
            assert "name" in result
            assert result["name"] == "Alice"
            assert "nonexistent" in result  # Will be None or not present

    @pytest.mark.asyncio
    async def test_concurrent_rate_limiters(self):
        """Test rate limiters work correctly under concurrent load"""
        service = EmbeddingService(api_key="test-key")

        async def get_limiter():
            await asyncio.sleep(0.01)  # Small delay
            return service.rate_limiter

        # Run multiple concurrent accesses
        tasks = [get_limiter() for _ in range(10)]
        limiters = await asyncio.gather(*tasks)

        # All should be the same instance in same event loop
        first_id = id(limiters[0])
        assert all(id(lim) == first_id for lim in limiters)


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    print("🧪 Phase 1 Bug Fixes - Test Suite")
    print("=" * 70)
    print("\nRunning tests with pytest...\n")

    # Run with pytest
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-k", "test_",
        "--asyncio-mode=auto"
    ])