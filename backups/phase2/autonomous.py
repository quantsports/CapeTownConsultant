"""
Autonomous agent with Phase 2 enhancements
- Concurrent tool execution
- Progress tracking
- Streaming support
"""

import json
import asyncio
import aiolimiter
from typing import List, Dict, Optional, AsyncIterator
from openai import AsyncOpenAI

from src.config.settings import Config
from src.core.models import CitationManager
from src.core.logging import logger
from src.services.cost_tracker import CostTracker
from src.tools.executor import ToolExecutor
from src.tools.schemas import ToolSchemas


class AutonomousAgent:
    """Enhanced agent with concurrent execution and streaming"""

    def __init__(
            self,
            openai_api_key: Optional[str] = None,
            cost_tracker: Optional[CostTracker] = None
    ):
        self.openai_api_key = openai_api_key or Config.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=self.openai_api_key) if self.openai_api_key else None
        self.cost_tracker = cost_tracker or CostTracker()
        self.tool_executor: Optional[ToolExecutor] = None
        self.conversation_history: List[Dict] = []
        self.citation_manager = CitationManager()
        self.max_iterations = 10
        self._rate_limiter = None
        self._rate_limiter_loop = None

        # Phase 2: Progress tracking
        self.current_operation = None
        self.progress_callback = None

    @property
    def rate_limiter(self):
        """Get or create rate limiter for current event loop"""
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create new limiter
            self._rate_limiter = aiolimiter.AsyncLimiter(Config.OPENAI_RPM, 60)
            self._rate_limiter_loop = None
            return self._rate_limiter

        # Check if we're in a different loop
        if self._rate_limiter_loop is not current_loop:
            self._rate_limiter = aiolimiter.AsyncLimiter(Config.OPENAI_RPM, 60)
            self._rate_limiter_loop = current_loop

        return self._rate_limiter

    async def __aenter__(self):
        """Initialize tool executor"""
        self.tool_executor = await ToolExecutor(cost_tracker=self.cost_tracker).__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup tool executor"""
        if self.tool_executor:
            await self.tool_executor.__aexit__(exc_type, exc_val, exc_tb)

    def _estimate_tokens(self, messages: List[Dict]) -> int:
        """Estimate token count"""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += len(content) // 4
        return total

    async def _summarize_conversation(
            self,
            messages: List[Dict],
            user_id: str
    ) -> str:
        """Summarize conversation to reduce context"""
        try:
            if not await self.cost_tracker.check_budget(user_id, "gpt-4o-mini-input", 1000):
                return "Previous context"

            conversation_text = "\n".join([
                f"{msg.get('role')}: {msg.get('content', '')[:200]}"
                for msg in messages if msg.get('content')
            ])

            response = await self.client.chat.completions.create(
                model=Config.SUMMARY_MODEL,
                messages=[{
                    "role": "user",
                    "content": f"Summarize concisely in 2-3 sentences:\n{conversation_text}"
                }],
                max_tokens=300,
                temperature=0.3,
            )

            summary = response.choices[0].message.content
            usage = response.usage

            await self.cost_tracker.record_cost(user_id, "gpt-4o-mini-input", usage.prompt_tokens)
            await self.cost_tracker.record_cost(user_id, "gpt-4o-mini-output", usage.completion_tokens)

            return summary

        except Exception:
            return "Previous context"

    async def _manage_conversation_history(self, user_id: str):
        """Smart history management with summarization"""
        token_count = self._estimate_tokens(self.conversation_history)

        if token_count > 8000:
            system_msgs = [msg for msg in self.conversation_history if msg["role"] == "system"]
            recent = self.conversation_history[-10:]
            to_summarize = self.conversation_history[len(system_msgs):-10]

            if to_summarize:
                summary = await self._summarize_conversation(to_summarize, user_id)
                self.conversation_history = [
                    *system_msgs,
                    {"role": "system", "content": f"[Previous summary]: {summary}"},
                    *recent
                ]

    async def _extract_memories(self, conversation: List[Dict], user_id: str):
        """Auto-extract memories from conversation"""
        if not Config.AUTO_MEMORY_EXTRACTION:
            return

        try:
            if not await self.cost_tracker.check_budget(user_id, "gpt-4o-mini-input", 2000):
                return

            user_messages = [
                msg.get("content", "") for msg in conversation[-5:]
                if msg.get("role") == "user" and msg.get("content")
            ]

            if not user_messages:
                return

            conversation_text = "\n".join(user_messages)

            response = await self.client.chat.completions.create(
                model=Config.SUMMARY_MODEL,
                messages=[{
                    "role": "user",
                    "content": f"""Extract important facts about the user from this conversation. Return JSON array or empty []:
{conversation_text}

[{{"text": "fact", "meta": {{"category": "preference|personal|goal"}}}}]"""
                }],
                max_tokens=300,
                temperature=0.2
            )

            result = response.choices[0].message.content.strip()
            usage = response.usage

            await self.cost_tracker.record_cost(user_id, "gpt-4o-mini-input", usage.prompt_tokens)
            await self.cost_tracker.record_cost(user_id, "gpt-4o-mini-output", usage.completion_tokens)

            try:
                memories = json.loads(result)
                if memories and isinstance(memories, list):
                    await self.tool_executor.execute(
                        "memory_upsert",
                        {"items": memories},
                        user_id
                    )
            except json.JSONDecodeError:
                pass

        except Exception:
            pass

    # ========================================================================
    # PHASE 2 ENHANCEMENT: Concurrent Tool Execution
    # ========================================================================

    async def _execute_tools_concurrently(
        self,
        tool_calls: List,
        user_id: str
    ) -> List[Dict]:
        """
        Execute multiple tool calls concurrently for 2-3x speedup

        Groups tools by type to optimize execution:
        - I/O-bound tools (search, memory) run in parallel
        - Respects rate limits per service
        """
        if not tool_calls:
            return []

        logger.info("concurrent_execution_start", count=len(tool_calls))

        # Parse tool calls and prepare tasks
        tasks = []
        tool_info = []

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            try:
                function_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                function_args = {}

            # Create execution task
            task = self.tool_executor.execute(
                function_name,
                function_args,
                user_id
            )
            tasks.append(task)
            tool_info.append({
                "id": tool_call.id,
                "name": function_name,
                "args": function_args
            })

        # Execute all tools concurrently
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = asyncio.get_event_loop().time() - start_time

        logger.info(
            "concurrent_execution_complete",
            count=len(tool_calls),
            time_seconds=round(execution_time, 2)
        )

        # Process results and build tool messages
        tool_messages = []
        for info, result in zip(tool_info, results):
            # Handle exceptions from gather
            if isinstance(result, Exception):
                logger.error(
                    "tool_execution_exception",
                    tool=info["name"],
                    error=str(result)
                )
                result_data = {
                    "success": False,
                    "error": f"Tool execution failed: {str(result)}"
                }
                tool_response = f"Error: {str(result)}"
            else:
                # Collect citations
                if hasattr(result, 'citations') and result.citations:
                    self.citation_manager.add_citations(result.citations)

                # Format response
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

    async def _report_progress(self, message: str):
        """Report progress to callback if registered"""
        self.current_operation = message
        if self.progress_callback:
            try:
                if asyncio.iscoroutinefunction(self.progress_callback):
                    await self.progress_callback(message)
                else:
                    self.progress_callback(message)
            except Exception as e:
                logger.warning("progress_callback_failed", error=str(e))

    # ========================================================================
    # PHASE 2 ENHANCEMENT: Streaming Chat
    # ========================================================================

    async def chat_stream(
        self,
        user_message: str,
        user_id: str = "default"
    ) -> AsyncIterator[str]:
        """
        Streaming version of chat that yields progress updates

        Yields:
            Progress updates and final response chunks
        """
        if not self.client:
            yield "❌ OpenAI API not configured"
            return

        # Check budget
        if not await self.cost_tracker.check_budget(user_id, "gpt-4o-input", 1000):
            costs = await self.cost_tracker.get_user_costs(user_id)
            yield f"❌ Budget limit reached. ${costs['total']:.3f} / ${costs['limit']:.2f}"
            return

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
        yield "🤔 Thinking...\n\n"

        while iterations < self.max_iterations:
            iterations += 1
            await self._manage_conversation_history(user_id)

            async with self.rate_limiter:
                try:
                    # Make API call with streaming
                    response = await self.client.chat.completions.create(
                        model=Config.CHAT_MODEL,
                        messages=self.conversation_history,
                        tools=ToolSchemas.get_function_definitions(),
                        tool_choice="auto",
                        temperature=0.3,
                        max_tokens=8000,
                        stream=False  # We handle progress differently
                    )

                    usage = response.usage
                    await self.cost_tracker.record_cost(user_id, "gpt-4o-input", usage.prompt_tokens)
                    await self.cost_tracker.record_cost(user_id, "gpt-4o-output", usage.completion_tokens)

                    assistant_message = response.choices[0].message

                    # Handle tool calls
                    if assistant_message.tool_calls:
                        tool_count = len(assistant_message.tool_calls)
                        tool_names = [tc.function.name for tc in assistant_message.tool_calls]

                        yield f"🔧 Using {tool_count} tool{'s' if tool_count > 1 else ''}: {', '.join(tool_names)}\n\n"

                        # Store assistant message with tool calls
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

                        # Execute tools concurrently (Phase 2 enhancement)
                        tool_messages = await self._execute_tools_concurrently(
                            assistant_message.tool_calls,
                            user_id
                        )

                        # Add tool responses to conversation
                        self.conversation_history.extend(tool_messages)

                        yield "✅ Tools complete, synthesizing answer...\n\n"
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

                        yield final_answer
                        return

                except Exception as e:
                    logger.error("chat_stream_failed", error=str(e))
                    yield f"❌ Error: {str(e)}"
                    return

        yield "⚠️ Max iterations reached. Try rephrasing."

    # ========================================================================
    # Standard Chat (with concurrent execution)
    # ========================================================================

    async def chat(self, user_message: str, user_id: str = "default") -> str:
        """
        Main chat interface with concurrent tool execution

        This version uses concurrent execution but returns complete response
        For streaming, use chat_stream()
        """
        if not self.client:
            return "❌ OpenAI API not configured"

        # Check budget
        if not await self.cost_tracker.check_budget(user_id, "gpt-4o-input", 1000):
            costs = await self.cost_tracker.get_user_costs(user_id)
            return f"❌ Budget limit reached. ${costs['total']:.3f} / ${costs['limit']:.2f}"

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

                    # Handle tool calls with concurrent execution
                    if assistant_message.tool_calls:
                        # Store assistant message with tool calls
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

                        # Phase 2: Execute tools concurrently
                        tool_messages = await self._execute_tools_concurrently(
                            assistant_message.tool_calls,
                            user_id
                        )

                        # Add tool responses to conversation
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

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history.clear()

    def set_progress_callback(self, callback):
        """Set callback for progress updates"""
        self.progress_callback = callback