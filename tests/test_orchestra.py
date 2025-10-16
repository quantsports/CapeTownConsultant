"""
Test suite for multi-agent orchestration system
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.workers.templates import WorkerType, WorkerTemplates
from src.workers.context_store import SharedContextStore
from src.workers.worker import BaseWorker, WorkerResult
from src.workers.orchestrator import WorkerOrchestrator


class TestWorkerTemplates:
    """Test worker template system"""

    def test_all_workers_have_templates(self):
        """Verify all worker types have templates"""
        for worker_type in WorkerType:
            template = WorkerTemplates.get_template(worker_type)
            assert template is not None
            assert "system_prompt" in template
            assert "required_vars" in template
            assert "tools" in template

    def test_variable_substitution(self):
        """Test template variable substitution"""
        template = "Hello {{name}}, your query is: {{query}}"
        variables = {"name": "Chef", "query": "menu planning"}

        result = WorkerTemplates.substitute_variables(template, variables)

        assert result == "Hello Chef, your query is: menu planning"
        assert "{{" not in result

    def test_recommend_workers_menu_query(self):
        """Test worker recommendation for menu queries"""
        query = "Design a new menu for my restaurant"
        workers = WorkerTemplates.recommend_workers(query, max_workers=3)

        assert WorkerType.MENU_PLANNER in workers
        assert len(workers) <= 3

    def test_recommend_workers_cost_query(self):
        """Test worker recommendation for cost queries"""
        query = "Analyze my food costs and pricing strategy"
        workers = WorkerTemplates.recommend_workers(query, max_workers=3)

        assert WorkerType.COST_ANALYST in workers

    def test_recommend_workers_complex_query(self):
        """Test worker recommendation for multi-domain query"""
        query = "Plan a restaurant opening with menu, budget, and marketing"
        workers = WorkerTemplates.recommend_workers(query, max_workers=3)

        # Should recommend multiple relevant workers
        assert len(workers) >= 2
        assert any(w in [WorkerType.MENU_PLANNER, WorkerType.COST_ANALYST,
                         WorkerType.MARKETING_STRATEGIST] for w in workers)

    def test_recommend_workers_fallback(self):
        """Test fallback to general consultant for ambiguous queries"""
        query = "I need help with something"
        workers = WorkerTemplates.recommend_workers(query, max_workers=3)

        assert WorkerType.GENERAL_CONSULTANT in workers


class TestSharedContextStore:
    """Test shared context store"""

    def test_initialization(self):
        """Test context store initialization"""
        store = SharedContextStore()

        assert "query" in store.context
        assert "user_profile" in store.context
        assert "worker_contributions" in store.context

    def test_initialize_with_data(self):
        """Test initializing context with query and profile"""
        store = SharedContextStore()

        query = "Test query"
        profile = {"name": "Chef John", "cuisine": "Italian"}

        store.initialize(query, profile)

        assert store.context["query"] == query
        assert store.context["user_profile"] == profile
        assert "parsed_query" in store.context

    def test_parse_query(self):
        """Test query parsing"""
        store = SharedContextStore()

        query = "Analyze and improve my menu with cost reduction"
        store.initialize(query, {})

        parsed = store.context["parsed_query"]

        assert "intents" in parsed
        assert "complexity" in parsed
        assert len(parsed["intents"]) > 0

    def test_add_contribution(self):
        """Test adding worker contribution"""
        store = SharedContextStore()
        store.initialize("Test query", {})

        data = {"findings": ["Finding 1", "Finding 2"]}
        store.add_contribution("menu_planner", data, confidence=0.9)

        contributions = store.get_all_contributions()

        assert len(contributions) == 1
        assert contributions[0].worker_type == "menu_planner"
        assert contributions[0].confidence == 0.9

    def test_get_relevant_context(self):
        """Test getting relevant context for a worker"""
        store = SharedContextStore()
        store.initialize("Design menu", {"role": "chef"})

        # Add contribution from another worker
        store.add_contribution("cost_analyst", {"data": "cost info"})

        # Get context for menu planner
        context = store.get_relevant_context("menu_planner")

        assert "query" in context
        assert "user_profile" in context
        assert "other_worker_insights" in context
        assert len(context["other_worker_insights"]) == 1

    def test_variable_dict_generation(self):
        """Test generating variables for template substitution"""
        store = SharedContextStore()
        store.initialize("Test query", {"name": "Chef"})

        variables = store.get_variable_dict()

        assert "query" in variables
        assert "user_profile" in variables
        assert "additional_context" in variables


class TestWorkerOrchestrator:
    """Test orchestrator functionality"""

    @pytest.mark.asyncio
    async def test_worker_selection(self):
        """Test automatic worker selection"""
        with patch('src.workers.orchestrator.ToolExecutor'), \
                patch('src.workers.orchestrator.ProfileManager'):
            orchestrator = WorkerOrchestrator(
                tool_executor=Mock(),
                profile_manager=Mock(),
                openai_api_key="test-key"
            )

            query = "Design a menu and analyze costs"
            workers = WorkerTemplates.recommend_workers(query, max_workers=3)

            # Should select menu and cost workers
            assert len(workers) >= 1
            assert any(w in [WorkerType.MENU_PLANNER, WorkerType.COST_ANALYST]
                       for w in workers)

    def test_get_available_workers(self):
        """Test listing available workers"""
        with patch('src.workers.orchestrator.ToolExecutor'), \
                patch('src.workers.orchestrator.ProfileManager'):
            orchestrator = WorkerOrchestrator(
                tool_executor=Mock(),
                profile_manager=Mock()
            )

            workers = orchestrator.get_available_workers()

            assert len(workers) == len(WorkerType)
            assert "menu_planner" in workers
            assert "cost_analyst" in workers


class TestWorkerResult:
    """Test worker result structure"""

    def test_worker_result_creation(self):
        """Test creating a worker result"""
        result = WorkerResult(
            worker_type=WorkerType.MENU_PLANNER,
            success=True,
            data={"findings": "test"},
            recommendations=["Rec 1", "Rec 2"],
            confidence=0.85,
            execution_time=1.5,
            sources=["http://example.com"]
        )

        assert result.success
        assert result.worker_type == WorkerType.MENU_PLANNER
        assert len(result.recommendations) == 2
        assert result.confidence == 0.85


class TestIntegration:
    """Integration tests"""

    @pytest.mark.asyncio
    @pytest.mark.skipif(not pytest.Config.getoption("--integration"),
                        reason="Integration tests require API keys")
    async def test_full_orchestration_flow(self):
        """Test complete orchestration flow (requires API keys)"""
        from src import AutonomousAssistant

        async with AutonomousAssistant(enable_orchestration=True) as assistant:
            response = await assistant.chat(
                "Quick menu suggestion for Italian restaurant",
                user_id="test_user"
            )

            assert response
            assert len(response) > 0


# Pytest configuration
def pytest_addoption(parser):
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests (requires API keys)"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])