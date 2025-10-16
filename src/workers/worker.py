"""
Base worker class and implementations
Workers are domain-specific agents that execute specialized tasks
"""

import asyncio
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from openai import AsyncOpenAI

from src.config.settings import Config
from src.core.logging import logger
from src.workers.templates import WorkerType, WorkerTemplates
from src.workers.context_store import SharedContextStore
from src.tools.executor import ToolExecutor


@dataclass
class WorkerResult:
    """Result from a worker execution"""
    worker_type: WorkerType
    success: bool
    data: Dict[str, Any]
    recommendations: List[str]
    confidence: float
    execution_time: float
    sources: List[str]
    error: Optional[str] = None
    metadata: Dict[str, Any] = None


class BaseWorker:
    """
    Base class for domain-specific workers
    Each worker is an autonomous agent with specialized expertise
    """

    def __init__(
            self,
            worker_type: WorkerType,
            context_store: SharedContextStore,
            tool_executor: ToolExecutor,
            openai_api_key: Optional[str] = None
    ):
        self.worker_type = worker_type
        self.context_store = context_store
        self.tool_executor = tool_executor
        self.openai_api_key = openai_api_key or Config.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=self.openai_api_key) if self.openai_api_key else None
        self.template = WorkerTemplates.get_template(worker_type)
        self.available_tools = WorkerTemplates.get_available_tools(worker_type)

    async def execute(self, user_id: str = "default") -> WorkerResult:
        """
        Execute the worker's task

        Returns:
            WorkerResult with findings, recommendations, and metadata
        """
        start_time = datetime.now()

        try:
            logger.info(
                "worker_started",
                worker_type=self.worker_type.value,
                user_id=user_id
            )

            # Get relevant context
            relevant_context = self.context_store.get_relevant_context(
                self.worker_type.value
            )

            # Prepare system prompt with variable substitution
            variables = self.context_store.get_variable_dict()
            system_prompt = WorkerTemplates.substitute_variables(
                self.template["system_prompt"],
                variables
            )

            # Execute worker's reasoning
            response = await self._run_worker_llm(
                system_prompt,
                relevant_context,
                user_id
            )

            # Parse and structure the response
            structured_result = self._structure_response(response)

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            result = WorkerResult(
                worker_type=self.worker_type,
                success=True,
                data=structured_result["data"],
                recommendations=structured_result["recommendations"],
                confidence=structured_result["confidence"],
                execution_time=execution_time,
                sources=structured_result["sources"],
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "context_used": len(str(relevant_context))
                }
            )

            # Add contribution to shared context
            self.context_store.add_contribution(
                worker_type=self.worker_type.value,
                data=structured_result["data"],
                confidence=structured_result["confidence"],
                sources=structured_result["sources"]
            )

            logger.info(
                "worker_completed",
                worker_type=self.worker_type.value,
                execution_time=execution_time,
                confidence=structured_result["confidence"]
            )

            return result

        except Exception as e:
            logger.error(
                "worker_failed",
                worker_type=self.worker_type.value,
                error=str(e)
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                data={},
                recommendations=[],
                confidence=0.0,
                execution_time=execution_time,
                sources=[],
                error=str(e)
            )

    async def _run_worker_llm(
            self,
            system_prompt: str,
            context: Dict[str, Any],
            user_id: str
    ) -> str:
        """
        Run the worker's LLM reasoning

        Args:
            system_prompt: The specialized prompt for this worker
            context: Relevant context from shared store
            user_id: User identifier

        Returns:
            LLM response text
        """
        if not self.client:
            raise ValueError("OpenAI API not configured")

        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"""Based on the following context, provide your specialized analysis and recommendations.

Context:
{context.get('query', '')}

Other Worker Insights:
{self._format_other_insights(context.get('other_worker_insights', []))}

Provide:
1. Your analysis
2. Specific recommendations (numbered list)
3. Confidence level (0.0-1.0)
4. Any sources or references

Format your response clearly with sections."""
            }
        ]

        # Get available tool definitions for this worker
        if self.available_tools:
            # Filter tool definitions to only include allowed tools
            from src.tools.schemas import ToolSchemas
            all_tools = ToolSchemas.get_function_definitions()
            worker_tools = [
                tool for tool in all_tools
                if tool["function"]["name"] in self.available_tools
            ]
        else:
            worker_tools = None

        # Call LLM
        response = await self.client.chat.completions.create(
            model=Config.CHAT_MODEL,
            messages=messages,
            tools=worker_tools if worker_tools else None,
            tool_choice="auto" if worker_tools else None,
            temperature=0.3,
            max_tokens=4000
        )

        # Handle tool calls if present
        assistant_message = response.choices[0].message

        if assistant_message.tool_calls:
            # Execute tools and continue conversation
            messages.append({
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

            # Execute tool calls
            for tool_call in assistant_message.tool_calls:
                import json
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                tool_result = await self.tool_executor.execute(
                    tool_name,
                    tool_args,
                    user_id
                )

                # Store tool result in context
                self.context_store.add_tool_result(tool_name, tool_result)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": json.dumps(tool_result.data if tool_result.success else {"error": tool_result.error})
                })

            # Get final response with tool results
            final_response = await self.client.chat.completions.create(
                model=Config.CHAT_MODEL,
                messages=messages,
                temperature=0.3,
                max_tokens=4000
            )

            return final_response.choices[0].message.content

        return assistant_message.content or ""

    def _format_other_insights(self, insights: List[Dict[str, Any]]) -> str:
        """Format insights from other workers"""
        if not insights:
            return "No prior insights available."

        formatted = []
        for insight in insights:
            formatted.append(
                f"- {insight['from_worker']}: {insight['summary']} "
                f"(confidence: {insight['confidence']:.2f})"
            )

        return "\n".join(formatted)

    def _structure_response(self, response: str) -> Dict[str, Any]:
        """
        Parse and structure the LLM response

        Args:
            response: Raw LLM response text

        Returns:
            Structured dictionary with data, recommendations, etc.
        """
        # Extract recommendations (numbered lists)
        recommendations = []
        import re
        rec_pattern = r'\d+\.\s+(.+?)(?=\n\d+\.|\n\n|$)'
        matches = re.finditer(rec_pattern, response, re.DOTALL)
        for match in matches:
            rec = match.group(1).strip()
            if len(rec) > 10:  # Filter out very short matches
                recommendations.append(rec)

        # Extract confidence if mentioned
        confidence = 0.8  # Default
        conf_pattern = r'confidence[:\s]+([0-9.]+)'
        conf_match = re.search(conf_pattern, response.lower())
        if conf_match:
            try:
                confidence = float(conf_match.group(1))
                if confidence > 1.0:
                    confidence = confidence / 100.0  # Convert percentage
            except ValueError:
                pass

        # Extract sources/references
        sources = []
        source_pattern = r'https?://[^\s)>]+'
        sources = re.findall(source_pattern, response)

        # The full response is the data
        data = {
            "full_analysis": response,
            "worker_type": self.worker_type.value,
            "key_points": self._extract_key_points(response),
        }

        return {
            "data": data,
            "recommendations": recommendations if recommendations else ["See full analysis above"],
            "confidence": confidence,
            "sources": sources
        }

    def _extract_key_points(self, text: str) -> List[str]:
        """Extract bullet points or key statements"""
        key_points = []

        # Look for bullet points
        bullet_pattern = r'[•\-*]\s+(.+)'
        bullets = re.findall(bullet_pattern, text)
        key_points.extend([b.strip() for b in bullets if len(b.strip()) > 10])

        # If no bullets found, extract sentences with strong keywords
        if not key_points:
            strong_keywords = [
                'important', 'critical', 'recommend', 'should', 'must',
                'key', 'essential', 'crucial', 'significant'
            ]
            sentences = text.split('.')
            for sentence in sentences:
                if any(keyword in sentence.lower() for keyword in strong_keywords):
                    clean = sentence.strip()
                    if 20 < len(clean) < 200:
                        key_points.append(clean)

        return key_points[:5]  # Limit to top 5