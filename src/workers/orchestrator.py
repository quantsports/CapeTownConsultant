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
            query,
            worker_results,
            synthesis
        )

        # Log completion
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            "orchestration_completed",
            duration=duration,
            workers_used=len(worker_results),
            success_count=sum(1 for r in worker_results if r.success)
        )

        return final_response

    async def _execute_workers_concurrently(
        self,
        workers: List[BaseWorker],
        user_id: str
    ) -> List[WorkerResult]:
        """
        Execute all workers concurrently with timeout protection

        Args:
            workers: List of worker instances to execute
            user_id: User identifier for logging

        Returns:
            List of WorkerResult objects
        """
        logger.info("executing_workers_concurrently", count=len(workers))

        async def execute_with_timeout(worker: BaseWorker) -> WorkerResult:
            """Execute single worker with timeout"""
            try:
                # 2-minute timeout per worker
                result = await asyncio.wait_for(
                    worker.execute(user_id),
                    timeout=120.0
                )
                logger.info(
                    "worker_completed",
                    worker_type=worker.worker_type.value,
                    success=result.success,
                    execution_time=result.execution_time
                )
                return result
            except asyncio.TimeoutError:
                logger.error(
                    "worker_timeout",
                    worker_type=worker.worker_type.value
                )
                # Return failed result
                return WorkerResult(
                    worker_type=worker.worker_type,
                    success=False,
                    data={},
                    recommendations=[],
                    confidence=0.0,
                    execution_time=120.0,
                    sources=[],
                    error="Worker execution timed out after 120 seconds"
                )
            except Exception as e:
                logger.error(
                    "worker_failed",
                    worker_type=worker.worker_type.value,
                    error=str(e)
                )
                return WorkerResult(
                    worker_type=worker.worker_type,
                    success=False,
                    data={},
                    recommendations=[],
                    confidence=0.0,
                    execution_time=0.0,
                    sources=[],
                    error=str(e)
                )

        # Execute all workers concurrently
        tasks = [execute_with_timeout(worker) for worker in workers]
        results = await asyncio.gather(*tasks)

        return list(results)

    async def _synthesize_results(
        self,
        query: str,
        worker_results: List[WorkerResult],
        context_store: SharedContextStore
    ) -> str:
        """
        Use LLM to synthesize worker results into coherent response

        Args:
            query: Original user query
            worker_results: Results from all workers
            context_store: Shared context store

        Returns:
            Synthesized response text
        """
        if not self.client:
            # Fallback: simple concatenation
            return self._simple_synthesis(query, worker_results)

        logger.info("synthesizing_results", worker_count=len(worker_results))

        # Build synthesis prompt
        synthesis_prompt = self._build_synthesis_prompt(query, worker_results)

        try:
            response = await self.client.chat.completions.create(
                model=Config.CHAT_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a master synthesizer that combines insights from domain specialists into comprehensive, actionable strategies.

Your job:
1. Identify common themes and synergies across specialist insights
2. Resolve any conflicts or contradictions
3. Prioritize recommendations by impact
4. Create a coherent, easy-to-follow action plan
5. Maintain the expertise and confidence levels from each specialist

Format your synthesis professionally with clear sections and actionable steps."""
                    },
                    {
                        "role": "user",
                        "content": synthesis_prompt
                    }
                ],
                temperature=0.4,
                max_tokens=4000
            )

            synthesis = response.choices[0].message.content or "Synthesis failed"
            logger.info("synthesis_completed", length=len(synthesis))
            return synthesis

        except Exception as e:
            logger.error("synthesis_failed", error=str(e))
            return self._simple_synthesis(query, worker_results)

    def _build_synthesis_prompt(
        self,
        query: str,
        worker_results: List[WorkerResult]
    ) -> str:
        """Build the prompt for LLM synthesis"""

        prompt_parts = [
            f"# Original Query",
            f"{query}\n",
            f"# Specialist Insights\n"
        ]

        for result in worker_results:
            if result.success:
                prompt_parts.append(f"## {result.worker_type.value.replace('_', ' ').title()}")
                prompt_parts.append(f"**Confidence:** {result.confidence * 100:.0f}%")
                prompt_parts.append(f"**Execution Time:** {result.execution_time:.1f}s\n")

                # Add key findings
                if result.data:
                    prompt_parts.append("**Key Findings:**")
                    for key, value in result.data.items():
                        if isinstance(value, str) and len(value) < 500:
                            prompt_parts.append(f"- {key}: {value}")
                        elif isinstance(value, (list, dict)):
                            prompt_parts.append(f"- {key}: {str(value)[:200]}...")

                # Add recommendations
                if result.recommendations:
                    prompt_parts.append("\n**Recommendations:**")
                    for rec in result.recommendations[:5]:  # Top 5
                        prompt_parts.append(f"- {rec}")

                # Add sources
                if result.sources:
                    prompt_parts.append(f"\n**Sources:** {', '.join(result.sources[:3])}")

                prompt_parts.append("\n")
            else:
                prompt_parts.append(f"## {result.worker_type.value.replace('_', ' ').title()}")
                prompt_parts.append(f"❌ Failed: {result.error}\n")

        prompt_parts.append("\n# Your Task")
        prompt_parts.append("Synthesize these specialist insights into a comprehensive, actionable strategy.")
        prompt_parts.append("Focus on:\n1. Integration of insights\n2. Prioritized recommendations\n3. Action steps\n4. Expected outcomes")

        return "\n".join(prompt_parts)

    def _simple_synthesis(
        self,
        query: str,
        worker_results: List[WorkerResult]
    ) -> str:
        """Fallback synthesis without LLM"""

        lines = [
            "# 🎯 Multi-Agent Analysis Results\n",
            f"**Query:** {query}\n",
            "---\n"
        ]

        successful = [r for r in worker_results if r.success]
        failed = [r for r in worker_results if not r.success]

        if successful:
            lines.append("## ✅ Specialist Insights\n")
            for result in successful:
                worker_name = result.worker_type.value.replace('_', ' ').title()
                lines.append(f"### {worker_name}")
                lines.append(f"*Confidence: {result.confidence * 100:.0f}%*\n")

                if result.recommendations:
                    for i, rec in enumerate(result.recommendations[:5], 1):
                        lines.append(f"{i}. {rec}")

                lines.append("")

        if failed:
            lines.append("\n## ⚠️ Incomplete Analysis")
            for result in failed:
                worker_name = result.worker_type.value.replace('_', ' ').title()
                lines.append(f"- {worker_name}: {result.error}")

        lines.append("\n---")
        lines.append(f"*Analysis completed using {len(successful)} specialist(s)*")

        return "\n".join(lines)

    def _format_final_response(
        self,
        query: str,
        worker_results: List[WorkerResult],
        synthesis: str
    ) -> str:
        """
        Format the final response with synthesis and metadata

        Args:
            query: Original query
            worker_results: Worker results
            synthesis: Synthesized text

        Returns:
            Formatted final response
        """

        # Header
        response_parts = [
            "🎭 **Multi-Agent Orchestration Response**\n",
            "=" * 70,
            ""
        ]

        # Main synthesis
        response_parts.append(synthesis)
        response_parts.append("")

        # Metadata footer
        response_parts.append("=" * 70)
        response_parts.append("## 📊 Orchestration Metadata\n")

        successful = [r for r in worker_results if r.success]
        total_time = sum(r.execution_time for r in worker_results)

        response_parts.append(f"**Workers Engaged:** {len(worker_results)}")
        response_parts.append(f"**Successful:** {len(successful)}/{len(worker_results)}")
        response_parts.append(f"**Total Execution Time:** {total_time:.1f}s")

        # List workers used
        worker_names = [r.worker_type.value.replace('_', ' ').title() for r in successful]
        response_parts.append(f"**Specialists:** {', '.join(worker_names)}")

        # Collect all unique sources
        all_sources = set()
        for result in successful:
            all_sources.update(result.sources)

        if all_sources:
            response_parts.append(f"\n**Sources Consulted:** {len(all_sources)}")

        return "\n".join(response_parts)