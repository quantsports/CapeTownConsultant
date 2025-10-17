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
            else:
                worker_types = WorkerTemplates.recommend_workers(query, max_workers)

            # Validate we have workers
            if not worker_types:
                logger.error("no_workers_selected", query=query[:100])
                return self._format_error_response(
                    "Could not determine appropriate specialists for this query. "
                    "Please try rephrasing your question."
                )

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

            # Check if all workers failed
            successful_results = [r for r in worker_results if r.success]
            if not successful_results:
                logger.error(
                    "all_workers_failed",
                    worker_count=len(worker_results),
                    user_id=user_id
                )
                return self._format_error_response(
                    "All specialists failed to complete analysis. Please try again.",
                    worker_results
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
                success_count=len(successful_results)
            )

            return final_response

        except Exception as e:
            logger.error(
                "orchestration_critical_error",
                error=str(e),
                user_id=user_id
            )
            duration = (datetime.now() - start_time).total_seconds()
            return self._format_error_response(
                f"Orchestration failed: {str(e)}",
                [],
                duration
            )