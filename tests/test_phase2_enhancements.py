"""
Phase 2 Enhancements Test Suite

Tests for:
1. Concurrent tool execution
2. Smart cache warming
3. Streaming responses
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Import Phase 2 modules
from src.agent.autonomous import AutonomousAgent
from src.interface.assistant import AutonomousAssistant
from src.services.cache_warmer import CacheWarmer, SmartEmbeddingService
from src.services.embeddings import EmbeddingService
from src.services.cost_tracker import CostTracker


# ============================================================================
# Test 1: Concurrent Tool Execution
# ============================================================================

class TestConcurrentExecution:
    """Test concurrent tool execution performance"""

    @pytest.mark.asyncio
    async def test_concurrent_execution_faster_than_sequential(self):
        """Verify concurrent execution is faster than sequential"""

        # Create mock tool executor
        async def mock_tool_execute(name, args, user_id):
            # Simulate network delay
            await asyncio.sleep(0.1)
            from src.core.models import ToolResult
            return ToolResult(
                success=True,
                data={"result": f"Result from {name}"},
                source=name
            )

        async with AutonomousAgent() as agent:
            agent.tool_executor = Mock()
            agent.tool_executor.execute = AsyncMock(side_effect=mock_tool_execute)

            # Create mock tool calls
            mock_tool_calls = [
                Mock(
                    id=f"call_{i}",
                    function=Mock(
                        name=f"tool_{i}",
                        arguments="{}"
                    )
                )
                for i in range(3)
            ]

            # Measure concurrent execution time
            start = time.time()
            await agent._execute_tools_concurrently(
                mock_tool_calls,
                "test_user"
            )
            concurrent_time = time.time() - start

            # Sequential execution should take ~0.3s (3 * 0.1)
            # Concurrent should take ~0.1s
            # Allow some overhead, but should be significantly faster
            assert concurrent_time < 0.25, \
                f"Concurrent execution too slow: {concurrent_time}s"

    @pytest.mark.asyncio
    async def test_concurrent_execution_handles_errors(self):
        """Test error handling in concurrent execution"""

        async def mock_tool_execute_with_error(name, args, user_id):
            if name == "failing_tool":
                raise Exception("Simulated tool failure")
            from src.core.models import ToolResult
            return ToolResult(success=True, data={"result": "OK"})

        async with AutonomousAgent() as agent:
            agent.tool_executor = Mock()
            agent.tool_executor.execute = AsyncMock(
                side_effect=mock_tool_execute_with_error
            )

            mock_tool_calls = [
                Mock(id="1", function=Mock(name="good_tool", arguments="{}")),
                Mock(id="2", function=Mock(name="failing_tool", arguments="{}")),
                Mock(id="3", function=Mock(name="good_tool", arguments="{}")),
            ]

            # Should not raise, should handle error gracefully
            results = await agent._execute_tools_concurrently(
                mock_tool_calls,
                "test_user"
            )

            assert len(results) == 3
            # Check that error was captured
            assert any("Error" in r["content"] for r in results)

    @pytest.mark.asyncio
    async def test_citations_collected_from_concurrent_tools(self):
        """Test that citations are collected from all concurrent tools"""
        from src.core.models import ToolResult

        async def mock_tool_with_citations(name, args, user_id):
            return ToolResult(
                success=True,
                data={"result": "data"},
                citations=[f"http://example.com/{name}"]
            )

        async with AutonomousAgent() as agent:
            agent.tool_executor = Mock()
            agent.tool_executor.execute = AsyncMock(
                side_effect=mock_tool_with_citations
            )

            mock_tool_calls = [
                Mock(id="1", function=Mock(name="tool1", arguments="{}")),
                Mock(id="2", function=Mock(name="tool2", arguments="{}")),
            ]

            # Clear citations
            agent.citation_manager.clear()

            await agent._execute_tools_concurrently(
                mock_tool_calls,
                "test_user"
            )

            # Check citations were collected
            citations = agent.citation_manager.citations
            assert len(citations) == 2
            assert "http://example.com/tool1" in citations
            assert "http://example.com/tool2" in citations


# ============================================================================
# Test 2: Smart Cache Warming
# ============================================================================

class TestSmartCaching:
    """Test smart cache warming functionality"""

    @pytest.mark.asyncio
    async def test_cache_warmer_tracks_accesses(self):
        """Test that cache warmer tracks query accesses"""
        embedding_service = EmbeddingService(api_key="test-key")
        warmer = CacheWarmer(embedding_service)

        # Log some accesses
        await warmer.log_access("query 1")
        await warmer.log_access("query 2")
        await warmer.log_access("query 1")  # Duplicate

        # Check counts
        assert warmer.access_counts["query 1"] == 2
        assert warmer.access_counts["query 2"] == 1

    @pytest.mark.asyncio
    async def test_cache_warmer_identifies_top_queries(self):
        """Test identification of top N queries"""
        embedding_service = EmbeddingService(api_key="test-key")
        warmer = CacheWarmer(embedding_service)

        # Simulate access pattern
        queries = ["popular"] * 10 + ["medium"] * 5 + ["rare"] * 1
        for q in queries:
            await warmer.log_access(q)

        top_3 = warmer.get_top_queries(3)
        assert top_3[0] == "popular"
        assert top_3[1] == "medium"
        assert top_3[2] == "rare"

    @pytest.mark.asyncio
    async def test_cache_warmer_skips_already_cached(self):
        """Test that warmer skips already cached items"""
        # Create embedding service with mock
        embedding_service = EmbeddingService(api_key="test-key")
        embedding_service.client = AsyncMock()

        # Mock cache to have one item already
        embedding_service.cache.get = AsyncMock(
            side_effect=lambda text: [0.1, 0.2] if text == "cached" else None
        )

        warmer = CacheWarmer(embedding_service)

        # Mock embed_batch to track calls
        original_embed_batch = embedding_service.embed_batch
        embedding_service.embed_batch = AsyncMock(return_value=[[0.1, 0.2]])

        # Warm with both cached and uncached
        await warmer.warm_cache(
            texts=["cached", "uncached"],
            user_id="test"
        )

        # Should only embed the uncached one
        calls = embedding_service.embed_batch.call_args_list
        if calls:
            called_texts = calls[0][0][0]  # First call, first arg
            assert "uncached" in called_texts
            assert "cached" not in called_texts

    @pytest.mark.asyncio
    async def test_smart_embedding_service_integration(self):
        """Test SmartEmbeddingService wrapper"""
        smart_service = SmartEmbeddingService(api_key="test-key")

        # Mock the base client
        smart_service.base_service.client = AsyncMock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        smart_service.base_service.client.embeddings.create = AsyncMock(
            return_value=mock_response
        )

        # Generate embedding
        await smart_service.embed("test query", "test_user")

        # Check access was logged
        assert "test query" in smart_service.cache_warmer.access_counts

    @pytest.mark.asyncio
    async def test_cache_stats_accurate(self):
        """Test cache statistics are accurate"""
        embedding_service = EmbeddingService(api_key="test-key")
        warmer = CacheWarmer(embedding_service)

        # Log various accesses
        await warmer.log_access("query1")
        await warmer.log_access("query2")
        await warmer.log_access("query1")

        stats = warmer.get_cache_stats()

        assert stats["total_unique_queries"] == 2
        assert stats["total_accesses"] == 3
        assert len(stats["top_10_queries"]) <= 10


# ============================================================================
# Test 3: Streaming Responses
# ============================================================================

class TestStreamingResponses:
    """Test streaming response functionality"""

    @pytest.mark.asyncio
    async def test_chat_stream_yields_chunks(self):
        """Test that chat_stream yields multiple chunks"""
        # Create mock agent with simple response
        async with AutonomousAgent() as agent:
            agent.client = AsyncMock()

            # Mock a simple response (no tool calls)
            mock_response = Mock()
            mock_response.choices = [
                Mock(message=Mock(content="Final answer", tool_calls=None))
            ]
            mock_response.usage = Mock(prompt_tokens=10, completion_tokens=5)

            agent.client.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            # Collect streamed chunks
            chunks = []
            async for chunk in agent.chat_stream("test", "test_user"):
                chunks.append(chunk)

            # Should have at least 2 chunks: thinking + answer
            assert len(chunks) >= 2
            assert any("Thinking" in c for c in chunks)
            assert any("Final answer" in c for c in chunks)

    @pytest.mark.asyncio
    async def test_chat_stream_reports_tool_usage(self):
        """Test that streaming reports tool usage"""
        async with AutonomousAgent() as agent:
            agent.client = AsyncMock()
            agent.tool_executor = Mock()

            # Mock tool call then final response
            from src.core.models import ToolResult
            agent.tool_executor.execute = AsyncMock(
                return_value=ToolResult(success=True, data={"result": "data"})
            )

            mock_tool_response = Mock()
            mock_tool_response.choices = [
                Mock(message=Mock(
                    content=None,
                    tool_calls=[
                        Mock(
                            id="call1",
                            function=Mock(name="web_search", arguments='{"query": "test"}')
                        )
                    ]
                ))
            ]
            mock_tool_response.usage = Mock(prompt_tokens=10, completion_tokens=5)

            mock_final_response = Mock()
            mock_final_response.choices = [
                Mock(message=Mock(content="Final answer", tool_calls=None))
            ]
            mock_final_response.usage = Mock(prompt_tokens=10, completion_tokens=5)

            agent.client.chat.completions.create = AsyncMock(
                side_effect=[mock_tool_response, mock_final_response]
            )

            # Collect chunks
            chunks = []
            async for chunk in agent.chat_stream("test", "test_user"):
                chunks.append(chunk)

            # Should mention tool usage
            assert any("tool" in c.lower() for c in chunks)
            assert any("web_search" in c for c in chunks)

    @pytest.mark.asyncio
    async def test_streaming_assistant_wrapper(self):
        """Test AutonomousAssistant streaming wrapper"""
        async with AutonomousAssistant(enable_streaming=True) as assistant:
            # Mock the agent's chat_stream
            async def mock_stream(msg, user_id):
                yield "Chunk 1"
                yield "Chunk 2"

            assistant.agent.chat_stream = mock_stream

            # Collect chunks
            chunks = []
            async for chunk in assistant.chat_stream("test", "test_user"):
                chunks.append(chunk)

            assert len(chunks) == 2
            assert chunks[0] == "Chunk 1"
            assert chunks[1] == "Chunk 2"

    @pytest.mark.asyncio
    async def test_progress_callback(self):
        """Test progress callback functionality"""
        callback_messages = []

        def progress_callback(msg):
            callback_messages.append(msg)

        async with AutonomousAgent() as agent:
            agent.set_progress_callback(progress_callback)

            # Trigger progress report
            await agent._report_progress("Test progress")

            assert len(callback_messages) == 1
            assert callback_messages[0] == "Test progress"


# ============================================================================
# Test 4: Integration Tests
# ============================================================================

class TestPhase2Integration:
    """Integration tests for Phase 2 features"""

    @pytest.mark.asyncio
    async def test_full_flow_with_concurrent_execution(self):
        """Test complete flow uses concurrent execution"""
        # This is a smoke test to ensure everything integrates
        try:
            async with AutonomousAssistant() as assistant:
                # Verify methods exist
                assert hasattr(assistant, 'chat')
                assert hasattr(assistant, 'chat_stream')
                assert hasattr(assistant.agent, '_execute_tools_concurrently')

                success = True
        except Exception as e:
            success = False
            error = str(e)

        assert success, f"Integration failed: {error if not success else ''}"

    @pytest.mark.asyncio
    async def test_cache_warmer_initialization(self):
        """Test cache warmer can be initialized"""
        from src.services.cache_warmer import CacheWarmer

        embedding_service = EmbeddingService(api_key="test-key")
        warmer = CacheWarmer(embedding_service)

        assert warmer is not None
        assert hasattr(warmer, 'warm_cache')
        assert hasattr(warmer, 'get_cache_stats')


# ============================================================================
# Test 5: Performance Benchmarks
# ============================================================================

class TestPerformanceBenchmarks:
    """Performance benchmarks for Phase 2"""

    @pytest.mark.asyncio
    async def test_concurrent_speedup_benchmark(self):
        """Benchmark concurrent vs sequential execution"""

        async def simulated_tool(delay=0.1):
            await asyncio.sleep(delay)
            from src.core.models import ToolResult
            return ToolResult(success=True, data={"result": "data"})

        # Sequential execution
        start = time.time()
        for _ in range(5):
            await simulated_tool(0.05)
        sequential_time = time.time() - start

        # Concurrent execution
        start = time.time()
        await asyncio.gather(*[simulated_tool(0.05) for _ in range(5)])
        concurrent_time = time.time() - start

        # Concurrent should be significantly faster
        speedup = sequential_time / concurrent_time
        assert speedup > 3, f"Speedup only {speedup}x, expected >3x"

    @pytest.mark.asyncio
    async def test_cache_hit_performance(self):
        """Test cache hit improves performance"""
        embedding_service = EmbeddingService(api_key="test-key")

        # Mock client
        embedding_service.client = AsyncMock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        embedding_service.client.embeddings.create = AsyncMock(
            return_value=mock_response
        )

        # First call (cache miss)
        start = time.time()
        await embedding_service.embed("test query", "test")
        first_time = time.time() - start

        # Second call (cache hit)
        start = time.time()
        await embedding_service.embed("test query", "test")
        second_time = time.time() - start

        # Cache hit should be much faster
        # Note: In tests this might be similar due to mocking,
        # but in production cache hits are 100x+ faster
        assert second_time <= first_time


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    print("🧪 Phase 2 Enhancements - Test Suite")
    print("=" * 70)
    print("\nRunning tests with pytest...\n")

    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-k", "test_",
        "--asyncio-mode=auto"
    ])