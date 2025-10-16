"""
Autonomous Agent with Multi-Agent Orchestration
Fixed to properly integrate orchestration system
"""

import asyncio
import json
from typing import Optional, Dict, List, AsyncIterator
from datetime import datetime
from openai import AsyncOpenAI
from aiolimiter import AsyncLimiter

from src.config.settings import Config
from src.core.logging import logger
from src.core.models import CitationManager
from src.services.cost_tracker import CostTracker
from src.services.embeddings import EmbeddingService
from src.memory.unified import UnifiedMemorySystem
from src.memory.profile import ProfileManager
from src.tools.executor import ToolExecutor
from src.tools.schemas import ToolSchemas


class AutonomousAgent:
    """
    Autonomous agent with tool orchestration and multi-agent support
    Intelligently routes between traditional and orchestration modes
    """

    def __init__(
        self,
        cost_tracker: Optional[CostTracker] = None,
        openai_api_key: Optional[str] = None,
        enable_orchestration: bool = True
    ):
        """
        Initialize agent

        Args:
            cost_tracker: Cost tracking instance
            openai_api_key: OpenAI API key
            enable_orchestration: Enable multi-agent orchestration
        """
        self.openai_api_key = openai_api_key or Config.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=self.openai_api_key) if self.openai_api_key else None

        # Core components
        self.cost_tracker = cost_tracker or CostTracker()
        self.citation_manager = CitationManager()
        self.conversation_history: List[Dict] = []
        self.max_iterations = Config.MAX_ITERATIONS

        # Rate limiting
        self.rate_limiter = AsyncLimiter(
            max_rate=Config.OPENAI_RPM,
            time_period=60
        )

        # Services (initialized in __aenter__)
        self.embedding_service: Optional[EmbeddingService] = None
        self.memory_system: Optional[UnifiedMemorySystem] = None
        self.tool_executor: Optional[ToolExecutor] = None
        self.profile_manager: Optional[ProfileManager] = None

        # Orchestration support
        self.enable_orchestration = enable_orchestration
        self.orchestrator = None  # Initialized in __aenter__

        # Progress tracking
        self.current_operation = ""
        self.progress_callback = None

    async def __aenter__(self):
        """Initialize services"""
        # Initialize embedding service
        self.embedding_service = EmbeddingService(
            api_key=self.openai_api_key,
            cost_tracker=self.cost_tracker
        )

        # Initialize profile manager
        self.profile_manager = ProfileManager()

        # Initialize vector memory
        from src.memory.vector import VectorMemory
        vector_memory = VectorMemory(embedding_service=self.embedding_service)

        # Initialize unified memory system
        self.memory_system = UnifiedMemorySystem(
            vector_memory=vector_memory,
            profile_manager=self.profile_manager
        )

        # Initialize tool executor
        self.tool_executor = await ToolExecutor(
            cost_tracker=self.cost_tracker
        ).__aenter__()

        # Initialize orchestrator if enabled
        if self.enable_orchestration:
            from src.workers.orchestrator import WorkerOrchestrator
            self.orchestrator = WorkerOrchestrator(
                tool_executor=self.tool_executor,
                profile_manager=self.profile_manager,
                openai_api_key=self.openai_api_key
            )
            logger.info("orchestration_initialized", status="enabled")
        else:
            logger.info("orchestration_disabled", mode="traditional")

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup services"""
        if self.tool_executor:
            await self.tool_executor.__aexit__(exc_type, exc_val, exc_tb)

    def _should_use_orchestration(self, query: str) -> bool:
        """
        Analyze query complexity to decide if orchestration is needed

        Returns:
            True if orchestration should be used, False for traditional mode
        """
        if not self.enable_orchestration or not self.orchestrator:
            return False

        query_lower = query.lower()

        # Rule 1: Long queries benefit from orchestration
        if len(query) > 100:
            logger.debug("orchestration_trigger", reason="long_query", length=len(query))
            return True

        # Rule 2: Multiple questions indicate complexity
        question_count = query.count('?')
        if question_count > 1:
            logger.debug("orchestration_trigger", reason="multiple_questions", count=question_count)
            return True

        # Rule 3: Complex action keywords
        action_keywords = [
            'analyze', 'design', 'plan', 'improve', 'optimize',
            'strategy', 'develop', 'create', 'build', 'recommend',
            'comprehensive', 'detailed', 'complete'
        ]
        action_matches = sum(1 for keyword in action_keywords if keyword in query_lower)
        if action_matches >= 2:
            logger.debug("orchestration_trigger", reason="complex_actions", matches=action_matches)
            return True

        # Rule 4: Multiple domain keywords indicate cross-functional query
        domain_keywords = [
            'menu', 'cost', 'pricing', 'marketing', 'staff',
            'operations', 'customer', 'service', 'supplier', 'financial'
        ]
        domain_matches = sum(1 for keyword in domain_keywords if keyword in query_lower)
        if domain_matches >= 2:
            logger.debug("orchestration_trigger", reason="multi_domain", domains=domain_matches)
            return True

        # Rule 5: Specific orchestration keywords
        orchestration_keywords = [
            'comprehensive plan', 'full strategy', 'complete analysis',
            'step by step', 'end to end', 'detailed breakdown'
        ]
        if any(phrase in query_lower for phrase in orchestration_keywords):
            logger.debug("orchestration_trigger", reason="orchestration_phrase")
            return True

        # Default to traditional mode for simple queries
        logger.debug("using_traditional_mode", reason="simple_query")
        return False

    async def chat(self, user_message: str, user_id: str = "default") -> str:
        """
        Main chat interface with intelligent orchestration routing

        Args:
            user_message: User's question or request
            user_id: User identifier

        Returns:
            Complete response string
        """
        if not self.client:
            return "❌ OpenAI API not configured"

        # Check budget
        if not await self.cost_tracker.check_budget(user_id, "gpt-4o-input", 1000):
            costs = await self.cost_tracker.get_user_costs(user_id)
            return f"❌ Budget limit reached. ${costs['total']:.3f} / ${costs['limit']:.2f}"

        # ORCHESTRATION ROUTING LOGIC
        if self._should_use_orchestration(user_message):
            logger.info(
                "routing_to_orchestration",
                query_length=len(user_message),
                user_id=user_id
            )
            try:
                response = await self.orchestrator.orchestrate(
                    query=user_message,
                    user_id=user_id,
                    max_workers=3
                )
                return response
            except Exception as e:
                logger.error("orchestration_failed", error=str(e))
                # Fall back to traditional mode
                logger.info("fallback_to_traditional", reason="orchestration_error")

        # TRADITIONAL MODE (existing implementation)
        return await self._traditional_chat(user_message, user_id)

    async def _traditional_chat(self, user_message: str, user_id: str = "default") -> str:
        """
        Traditional single-agent chat mode

        This is the original implementation without orchestration
        """
        self.citation_manager.clear()

        # Initialize conversation
        system_message = {
            "role": "system",
            "content": """Autonomous assistant with tools.

TOOL COST STRATEGY:
1. wiki_fetch: FREE - Try first for encyclopedic topics
2. web_search: CHEAP - Default for most queries
3. google_search: MEDIUM - Use if web_search fails
4. perplexity_search: EXPENSIVE - Only for complex analysis

Always cite sources [1], [2]. Store important user info automatically."""
        }

        if not self.conversation_history or self.conversation_history[0]["role"] != "system":
            self.conversation_history = [system_message]

        self.conversation_history.append({"role": "user", "content": user_message})

        iterations = 0

        while iterations < self.max_iterations:
            iterations += 1
            await self._manage_conversation_history(user_id)

            async with self.rate_limiter:
                try:
                    response = await self.client.chat.completions.create(
                        model=Config.CHAT_MODEL,
                        messages=self.conversation_history,
                        tools=ToolSchemas.get_function_definitions(),
                        tool_choice="auto",
                        temperature=0.3,
                        max_tokens=8000
                    )

                    usage = response.usage
                    await self.cost_tracker.record_cost(user_id, "gpt-4o-input", usage.prompt_tokens)
                    await self.cost_tracker.record_cost(user_id, "gpt-4o-output", usage.completion_tokens)

                    assistant_message = response.choices[0].message

                    # Handle tool calls
                    if assistant_message.tool_calls:
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": assistant_message.content,
                            "tool_calls": [
                                {
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {
                                        "name": tc.function.name,
                                        "arguments": tc.function.arguments
                                    }
                                }
                                for tc in assistant_message.tool_calls
                            ]
                        })

                        # Execute tools
                        tool_messages = await self._execute_tools_concurrently(
                            assistant_message.tool_calls,
                            user_id
                        )

                        self.conversation_history.extend(tool_messages)
                        continue

                    else:
                        # Final answer
                        final_answer = assistant_message.content or "I couldn't generate a response."
                        final_answer += self.citation_manager.format_citations()

                        if Config.ENABLE_COST_TRACKING:
                            costs = await self.cost_tracker.get_user_costs(user_id)
                            final_answer += f"\n\n💰 Usage: ${costs['total']:.4f} / ${costs['limit']:.2f}"

                        self.conversation_history.append({
                            "role": "assistant",
                            "content": final_answer
                        })

                        # Extract memories
                        await self._extract_memories(self.conversation_history[-6:], user_id)

                        return final_answer

                except Exception as e:
                    logger.error("chat_failed", error=str(e))
                    return f"❌ Error: {str(e)}"

        return "⚠️ Max iterations reached. Try rephrasing."

    async def _execute_tools_concurrently(self, tool_calls, user_id: str) -> List[Dict]:
        """Execute multiple tools in parallel"""
        tool_infos = []

        for tc in tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}

            tool_infos.append({
                "id": tc.id,
                "name": tc.function.name,
                "args": args
            })

        # Execute all tools concurrently
        tasks = [
            self.tool_executor.execute(info["name"], info["args"], user_id)
            for info in tool_infos
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Format responses
        tool_messages = []
        for info, result in zip(tool_infos, results):
            if isinstance(result, Exception):
                tool_response = f"Error: {str(result)}"
            else:
                if result.success:
                    data_str = json.dumps(result.data, indent=2)
                    if len(data_str) > 2000:
                        data_str = data_str[:2000] + "\n... (truncated)"
                    tool_response = f"Success from {result.source or info['name']}:\n{data_str}"
                else:
                    tool_response = f"Error: {result.error}"

            tool_messages.append({
                "role": "tool",
                "tool_call_id": info["id"],
                "name": info["name"],
                "content": tool_response
            })

        return tool_messages

    async def _manage_conversation_history(self, user_id: str):
        """Manage conversation history to stay within token limits"""
        # Simple truncation strategy - keep system message and recent history
        if len(self.conversation_history) > Config.MAX_HISTORY_MESSAGES:
            system_msg = self.conversation_history[0]
            recent = self.conversation_history[-(Config.MAX_HISTORY_MESSAGES - 1):]
            self.conversation_history = [system_msg] + recent

    async def _extract_memories(self, recent_messages: List[Dict], user_id: str):
        """Extract and store important information from conversation"""
        # Simplified memory extraction
        pass

    def set_progress_callback(self, callback):
        """Set callback for progress updates"""
        self.progress_callback = callback

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        self.citation_manager.clear()

    async def chat_stream(self, user_message: str, user_id: str = "default") -> AsyncIterator[str]:
        """
        Streaming version - delegates to orchestrator if needed
        """
        if self._should_use_orchestration(user_message):
            # Orchestration doesn't support streaming yet, return complete response
            result = await self.chat(user_message, user_id)
            yield result
        else:
            # Use traditional streaming (simplified version)
            result = await self._traditional_chat(user_message, user_id)
            yield result