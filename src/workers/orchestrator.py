"""
Worker Orchestrator
Coordinates multiple specialized workers and synthesizes their results
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from openai import AsyncOpenAI
import re
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
        start_time = datetime.now()

        logger.info(
            "orchestration_started",
            query_length=len(query),
            user_id=user_id,
            max_workers=max_workers
        )

        # Initialize shared context store
        context_store = SharedContextStore()

        # Load user profile
        user_profile = await self.profile_manager.read(user_id)

        # Initialize context
        context_store.initialize(query, user_profile)

        # Determine which workers to spawn
        if force_workers:
            worker_types = force_workers[:max_workers]
        else:
            worker_types = WorkerTemplates.recommend_workers(query, max_workers)

        logger.info(
            "workers_selected",
            workers=[w.value for w in worker_types]
        )

        # Create worker instances
        workers = [
            BaseWorker(
                worker_type=worker_type,
                context_store=context_store,
                tool_executor=self.tool_executor,
                openai_api_key=self.openai_api_key
            )
            for worker_type in worker_types
        ]

        # Execute workers concurrently
        worker_results = await self._execute_workers_concurrently(
            workers,
            user_id
        )

        # Synthesize results
        synthesis = await self._synthesize_results(
            query,
            worker_results,
            context_store
        )

        # Store synthesis in context
        context_store.set_synthesis(synthesis)

        # Format final response
        final_response = self._format_final_response(
            synthesis,
            worker_results,
            context_store
        )

        execution_time = (datetime.now() - start_time).total_seconds()

        logger.info(
            "orchestration_completed",
            workers_executed=len(worker_results),
            execution_time=execution_time,
            success_rate=sum(1 for r in worker_results if r.success) / len(worker_results)
        )

        return final_response

    async def _execute_workers_concurrently(
            self,
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
                if isinstance(result, Exception):
                    logger.error(
                        "worker_exception",
                        worker=workers[i].worker_type.value,
                        error=str(result)
                    )
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
                    valid_results.append(result)

            return valid_results

        except asyncio.TimeoutError:
            logger.error("worker_execution_timeout")
            return []

    async def _synthesize_results(
            self,
            query: str,
            worker_results: List[WorkerResult],
            context_store: SharedContextStore
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
            return self._basic_synthesis(worker_results)

        # Prepare synthesis prompt
        synthesis_prompt = self._build_synthesis_prompt(
            query,
            worker_results
        )

        try:
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
            return self._basic_synthesis(worker_results)

    def _build_synthesis_prompt(
            self,
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

    def _basic_synthesis(
            self,
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

    def _format_final_response(
            self,
            synthesis: Dict[str, Any],
            worker_results: List[WorkerResult],
            context_store: SharedContextStore
    ) -> str:
        """Format the final response for the user"""
        response_parts = []

        # Add synthesis
        response_parts.append("# 🎯 Strategic Consultation\n")
        response_parts.append(synthesis["synthesis"])

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

    def get_available_workers(self) -> List[str]:
        """Get list of available worker types"""
        return [wt.value for wt in WorkerType]

    async def explain_workers(self, query: str) -> str:
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