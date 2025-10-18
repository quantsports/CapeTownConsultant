"""
Worker Orchestrator - Complete Implementation
Coordinates multiple specialized workers and synthesizes their results
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from openai import AsyncOpenAI

from src.config.settings import Config
from src.core.logging import logger
from src.workers.worker import BaseWorker, WorkerResult
from src.workers.templates import WorkerType, WorkerTemplates
from src.workers.context_store import SharedContextStore
from src.tools.executor import ToolExecutor
from src.memory.profile import ProfileManager


class WorkerOrchestrator:
    """
    Orchestrates multiple domain-specific workers
    Manages concurrent execution and synthesizes results
    """

    def __init__(
        self,
        tool_executor: ToolExecutor,
        profile_manager: ProfileManager,
        openai_api_key: Optional[str] = None
    ):
        self.tool_executor = tool_executor
        self.profile_manager = profile_manager
        self.openai_api_key = openai_api_key or Config.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=self.openai_api_key) if self.openai_api_key else None

    async def orchestrate(
        self,
        query: str,
        user_id: str = "default",
        max_workers: int = 3,
        force_workers: Optional[List[WorkerType]] = None
    ) -> str:
        """
        Main orchestration method

        Args:
            query: User query
            user_id: User identifier
            max_workers: Maximum number of workers to spawn
            force_workers: Optional list to force specific workers

        Returns:
            Synthesized response from all workers
        """
        # Validate inputs
        if not query or not query.strip():
            logger.error("orchestration_empty_query", user_id=user_id)
            return "❌ Error: Empty query provided"

        if max_workers < 1:
            logger.warning("invalid_max_workers", max_workers=max_workers, user_id=user_id)
            max_workers = 1
        elif max_workers > 10:
            logger.warning("max_workers_capped", requested=max_workers, capped=10)
            max_workers = 10

        start_time = datetime.now()

        logger.info(
            "orchestration_started",
            query_length=len(query),
            user_id=user_id,
            max_workers=max_workers
        )

        # Terminal output for orchestration start
        print("\n" + "="*80)
        print(f"🚀 ORCHESTRATION STARTED")
        print(f"   Query: {query[:70]}{'...' if len(query) > 70 else ''}")
        print(f"   User: {user_id} | Max Workers: {max_workers}")
        print("="*80)

        try:
            # Initialize shared context store
            context_store = SharedContextStore()

            # Load user profile
            user_profile = await self.profile_manager.read(user_id)

            # Initialize context
            context_store.initialize(query, user_profile)

            # Determine which workers to spawn
            if force_workers:
                worker_types = force_workers[:max_workers]
                print(f"\n🔧 Using FORCED workers: {[w.value for w in worker_types]}")
            else:
                worker_types = WorkerTemplates.recommend_workers(query, max_workers)
                print(f"\n🤖 AI-SELECTED workers: {[w.value for w in worker_types]}")

            # Validate we have workers
            if not worker_types:
                logger.error("no_workers_selected", query=query[:100])
                print("❌ ERROR: No workers could be selected for this query")
                return WorkerOrchestrator._format_error_response(
                    "Could not determine appropriate specialists for this query. "
                    "Please try rephrasing your question."
                )

            logger.info(
                "workers_selected",
                workers=[w.value for w in worker_types]
            )

            # Create worker instances with logging
            print(f"\n📦 CREATING {len(worker_types)} SPECIALIZED WORKERS...")
            workers = []
            for i, worker_type in enumerate(worker_types, 1):
                worker_name = worker_type.value.replace('_', ' ').title()
                print(f"   [{i}/{len(worker_types)}] Initializing: {worker_name}")

                worker = BaseWorker(
                    worker_type=worker_type,
                    context_store=context_store,
                    tool_executor=self.tool_executor,
                    openai_api_key=self.openai_api_key
                )
                workers.append(worker)

                # Get worker template info
                template = WorkerTemplates.get_template(worker_type)
                tools = template.get('tools', [])
                print(f"       └─ Tools: {', '.join(tools[:3])}{' ...' if len(tools) > 3 else ''}")

            print(f"\n✅ All workers initialized successfully\n")

            # Execute workers concurrently
            print("⚡ EXECUTING WORKERS CONCURRENTLY...")
            print("-" * 80)

            worker_results = await WorkerOrchestrator._execute_workers_concurrently(
                workers,
                user_id
            )

            # Check if all workers failed
            successful_results = [r for r in worker_results if r.success]
            failed_results = [r for r in worker_results if not r.success]

            print("\n" + "-" * 80)
            print(f"📊 WORKER EXECUTION SUMMARY:")
            print(f"   ✅ Successful: {len(successful_results)}/{len(worker_results)}")
            print(f"   ❌ Failed: {len(failed_results)}/{len(worker_results)}")

            if not successful_results:
                logger.error(
                    "all_workers_failed",
                    worker_count=len(worker_results),
                    user_id=user_id
                )
                print("\n❌ CRITICAL: All workers failed!")
                return WorkerOrchestrator._format_error_response(
                    "All specialists failed to complete analysis. Please try again.",
                    worker_results
                )

            # Show individual worker results
            print("\n📋 DETAILED RESULTS:")
            for result in worker_results:
                worker_name = result.worker_type.value.replace('_', ' ').title()
                status = "✅" if result.success else "❌"
                print(f"   {status} {worker_name:30} | Confidence: {result.confidence:.1%} | Time: {result.execution_time:.2f}s")

            # Synthesize results
            print("\n🔮 SYNTHESIZING RESULTS...")
            synthesis = await self._synthesize_results(
                query,
                worker_results
            )
            print(f"   ✅ Synthesis complete using: {synthesis.get('approach', 'unknown')}")

            # Store synthesis in context
            context_store.set_synthesis(synthesis)

            # Format final response
            final_response = WorkerOrchestrator._format_final_response(
                worker_results,
                synthesis
            )

            # Log completion
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                "orchestration_completed",
                duration=duration,
                workers_used=len(worker_results),
                success_count=len(successful_results)
            )

            print("\n" + "="*80)
            print(f"🎉 ORCHESTRATION COMPLETED SUCCESSFULLY")
            print(f"   Duration: {duration:.2f}s | Workers: {len(successful_results)}/{len(worker_results)}")
            print("="*80 + "\n")

            return final_response

        except Exception as e:
            logger.error(
                "orchestration_critical_error",
                error=str(e),
                user_id=user_id
            )
            duration = (datetime.now() - start_time).total_seconds()
            print(f"\n💥 CRITICAL ERROR: {str(e)}")
            print(f"   Duration before failure: {duration:.2f}s\n")
            return WorkerOrchestrator._format_error_response(
                f"Orchestration failed: {str(e)}",
                [],
                duration
            )

    @staticmethod
    async def _execute_workers_concurrently(
            workers: List[BaseWorker],
            user_id: str
    ) -> List[WorkerResult]:
        """
        Execute multiple workers concurrently

        Args:
            workers: List of worker instances
            user_id: User identifier

        Returns:
            List of worker results
        """
        # Print worker execution start
        for i, worker in enumerate(workers, 1):
            worker_name = worker.worker_type.value.replace('_', ' ').title()
            print(f"   [{i}] Starting: {worker_name}...")

        tasks = [worker.execute(user_id) for worker in workers]

        # Execute with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=120.0  # 2 minute timeout
            )

            # Filter out exceptions
            valid_results = []
            for i, result in enumerate(results):
                worker_name = workers[i].worker_type.value.replace('_', ' ').title()

                if isinstance(result, Exception):
                    logger.error(
                        "worker_exception",
                        worker=workers[i].worker_type.value,
                        error=str(result)
                    )
                    print(f"   ❌ {worker_name} FAILED: {str(result)[:60]}")
                    # Create failed result
                    valid_results.append(WorkerResult(
                        worker_type=workers[i].worker_type,
                        success=False,
                        data={},
                        recommendations=[],
                        confidence=0.0,
                        execution_time=0.0,
                        sources=[],
                        error=str(result)
                    ))
                else:
                    status = "✅" if result.success else "⚠️"
                    print(f"   {status} {worker_name} completed ({result.execution_time:.2f}s)")
                    valid_results.append(result)

            return valid_results

        except asyncio.TimeoutError:
            logger.error("worker_execution_timeout")
            print("   ⏰ TIMEOUT: Worker execution exceeded 120s limit")
            return []

    async def _synthesize_results(
            self,
            query: str,
            worker_results: List[WorkerResult]
    ) -> Dict[str, Any]:
        """
        Synthesize results from multiple workers using LLM

        Args:
            query: Original query
            worker_results: Results from all workers
            context_store: Shared context

        Returns:
            Synthesized analysis
        """
        if not self.client:
            print("   ℹ️  Using basic synthesis (no LLM available)")
            return WorkerOrchestrator._basic_synthesis(worker_results)

        # Prepare synthesis prompt
        synthesis_prompt = WorkerOrchestrator._build_synthesis_prompt(
            query,
            worker_results
        )

        try:
            print("   🤖 Calling LLM for synthesis...")
            response = await self.client.chat.completions.create(
                model=Config.CHAT_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a Senior Restaurant Consultant synthesizing insights from multiple domain experts.

Your task:
1. Integrate insights from all specialists
2. Identify common themes and conflicts
3. Provide a coherent, actionable strategy
4. Highlight priorities and next steps

Be concise, strategic, and practical."""
                    },
                    {
                        "role": "user",
                        "content": synthesis_prompt
                    }
                ],
                temperature=0.3,
                max_tokens=3000
            )

            synthesis_text = response.choices[0].message.content

            return {
                "synthesis": synthesis_text,
                "approach": "llm_synthesis",
                "worker_count": len(worker_results),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("synthesis_failed", error=str(e))
            print(f"   ⚠️  LLM synthesis failed: {str(e)[:60]}")
            print("   ℹ️  Falling back to basic synthesis")
            return WorkerOrchestrator._basic_synthesis(worker_results)

    @staticmethod
    def _build_synthesis_prompt(
            query: str,
            worker_results: List[WorkerResult]
    ) -> str:
        """Build prompt for synthesis"""
        prompt_parts = [
            f"Original Query: {query}\n",
            "\n=== SPECIALIST INSIGHTS ===\n"
        ]

        for result in worker_results:
            if result.success:
                prompt_parts.append(f"\n## {result.worker_type.value.replace('_', ' ').title()}")
                prompt_parts.append(f"Confidence: {result.confidence:.2f}")

                if result.recommendations:
                    prompt_parts.append("\nRecommendations:")
                    for i, rec in enumerate(result.recommendations[:5], 1):
                        prompt_parts.append(f"{i}. {rec}")

                # Add key points from data
                if "key_points" in result.data:
                    prompt_parts.append("\nKey Points:")
                    for point in result.data["key_points"][:3]:
                        prompt_parts.append(f"- {point}")

                prompt_parts.append("")

        prompt_parts.append("\n=== YOUR TASK ===")
        prompt_parts.append(
            "Synthesize these specialist insights into a coherent, actionable response. "
            "Prioritize recommendations, note any conflicts, and provide clear next steps."
        )

        return "\n".join(prompt_parts)

    @staticmethod
    def _basic_synthesis(
            worker_results: List[WorkerResult]
    ) -> Dict[str, Any]:
        """Basic synthesis without LLM (fallback)"""
        all_recommendations = []
        all_sources = []
        total_confidence = 0.0
        success_count = 0

        for result in worker_results:
            if result.success:
                all_recommendations.extend(result.recommendations)
                all_sources.extend(result.sources)
                total_confidence += result.confidence
                success_count += 1

        avg_confidence = total_confidence / success_count if success_count > 0 else 0.0

        synthesis_text = "Based on analysis from multiple specialists:\n\n"

        for result in worker_results:
            if result.success:
                synthesis_text += f"**{result.worker_type.value.replace('_', ' ').title()}** "
                synthesis_text += f"(confidence: {result.confidence:.0%}):\n"
                for rec in result.recommendations[:3]:
                    synthesis_text += f"- {rec}\n"
                synthesis_text += "\n"

        return {
            "synthesis": synthesis_text,
            "approach": "basic_synthesis",
            "worker_count": len(worker_results),
            "avg_confidence": avg_confidence,
            "timestamp": datetime.now().isoformat()
        }

    @staticmethod
    def _format_final_response(
            worker_results: List[WorkerResult],
            synthesis: Dict[str, Any]
    ) -> str:
        """Format the final response for the user"""
        # Add synthesis
        response_parts = [
            "# 🎯 Strategic Consultation\n",
            synthesis["synthesis"]
        ]

        # Add section divider
        response_parts.append("\n" + "=" * 70 + "\n")

        # Add specialist contributions
        response_parts.append("## 👥 Specialist Insights\n")

        for result in worker_results:
            if result.success:
                worker_name = result.worker_type.value.replace('_', ' ').title()
                response_parts.append(f"\n### {worker_name}")
                response_parts.append(f"*Confidence: {result.confidence:.0%}*\n")

                if result.recommendations:
                    for i, rec in enumerate(result.recommendations[:5], 1):
                        response_parts.append(f"{i}. {rec}")

                response_parts.append("")

        # Add sources if available
        all_sources = []
        for result in worker_results:
            all_sources.extend(result.sources)

        if all_sources:
            unique_sources = list(set(all_sources))[:10]
            response_parts.append("\n" + "=" * 70)
            response_parts.append("\n## 📚 Sources\n")
            for i, source in enumerate(unique_sources, 1):
                response_parts.append(f"[{i}] {source}")

        # Add metadata
        response_parts.append("\n" + "=" * 70)
        response_parts.append(f"\n*Analysis by {len(worker_results)} specialist(s) • "
                              f"Orchestrated consultation • "
                              f"{datetime.now().strftime('%Y-%m-%d %H:%M')}*")

        return "\n".join(response_parts)

    @staticmethod
    def _format_error_response(
            error_message: str,
            worker_results: List[WorkerResult] = None,
            duration: float = 0.0
    ) -> str:
        """Format an error response for the user"""
        response_parts = [
            "# ❌ Orchestration Error\n",
            f"**Error:** {error_message}\n"
        ]

        if worker_results:
            # Show which workers succeeded/failed
            response_parts.append("\n## Worker Status\n")
            for result in worker_results:
                status = "✅" if result.success else "❌"
                worker_name = result.worker_type.value.replace('_', ' ').title()
                response_parts.append(f"{status} {worker_name}")
                if not result.success and result.error:
                    response_parts.append(f"   Error: {result.error}")

        if duration > 0:
            response_parts.append(f"\n*Duration: {duration:.2f}s*")

        response_parts.append("\n\nPlease try rephrasing your query or try again later.")

        return "\n".join(response_parts)

    @staticmethod
    def get_available_workers() -> List[str]:
        """Get list of available worker types"""
        return [wt.value for wt in WorkerType]

    @staticmethod
    async def explain_workers(query: str) -> str:
        """Explain which workers would be used for a query"""
        worker_types = WorkerTemplates.recommend_workers(query, max_workers=5)

        explanation = [
            f"For query: '{query[:100]}...'\n",
            "Recommended specialists:\n"
        ]

        for i, wt in enumerate(worker_types, 1):
            template = WorkerTemplates.get_template(wt)
            explanation.append(
                f"{i}. **{wt.value.replace('_', ' ').title()}** "
                f"(Priority: {template.get('priority', 3)})"
            )
            explanation.append(f"   Tools: {', '.join(template.get('tools', []))}\n")

        return "\n".join(explanation)

    def add_tool_result(self, tool_name: str, result: Any):
        """
        Store tool execution result

        Args:
            tool_name: Name of the tool executed
            result: Tool execution result
        """
        if not hasattr(self, "tool_results"):
            self.tool_results = {}

        if tool_name not in self.tool_results:
            self.tool_results[tool_name] = []

        self.tool_results[tool_name].append(
            {"result": result, "timestamp": datetime.now().isoformat()}
        )

        logger.debug(
            "tool_result_stored",
            tool_name=tool_name,
            result_count=len(self.tool_results[tool_name]),
        )
