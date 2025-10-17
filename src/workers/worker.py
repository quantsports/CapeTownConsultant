"""
Base worker class and implementations
Workers are domain-specific agents that execute specialized tasks
"""

import asyncio
import json
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
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
    metadata: Dict[str, Any] = field(default_factory=dict)


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

            # Validate dependencies
            if not self.client:
                raise ValueError("OpenAI API client not configured")

            if not self.tool_executor:
                raise ValueError("Tool executor not configured")

            # Check if tool executor is initialized (if it has the property)
            if hasattr(self.tool_executor, 'is_initialized') and not self.tool_executor.is_initialized:
                raise ValueError("Tool executor not initialized")

            # Get relevant context with error handling
            try:
                relevant_context = self.context_store.get_relevant_context(
                    self.worker_type.value
                )
                if relevant_context is None:
                    relevant_context = {}
                    logger.warning("context_store_returned_none", worker_type=self.worker_type.value)
            except Exception as e:
                logger.warning("context_retrieval_failed",
                              worker_type=self.worker_type.value,
                              error=str(e))
                relevant_context = {}

            # Get variables with error handling
            try:
                variables = self.context_store.get_variable_dict()
                if variables is None:
                    variables = {}
            except Exception as e:
                logger.warning("variable_dict_retrieval_failed", error=str(e))
                variables = {}

            # Prepare system prompt with variable substitution
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

            # Validate response
            if not response or not response.strip():
                raise ValueError("Empty response from LLM")

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
                    "context_used": len(str(relevant_context)),
                    "user_id": user_id
                }
            )

            # Add contribution to shared context with error handling
            try:
                self.context_store.add_contribution(
                    worker_type=self.worker_type.value,
                    data=structured_result["data"],
                    confidence=structured_result["confidence"],
                    sources=structured_result["sources"]
                )
            except Exception as e:
                logger.warning("context_contribution_failed",
                              worker_type=self.worker_type.value,
                              error=str(e))
                result.metadata["context_store_error"] = str(e)

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
                error=str(e),
                user_id=user_id
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
                error=str(e),
                metadata={"timestamp": datetime.now().isoformat(), "user_id": user_id}
            )

    def _serialize_tool_result(self, tool_result) -> str:
        """Safely serialize tool result for LLM consumption"""
        try:
            if tool_result.success:
                data = tool_result.data
                # Handle common non-serializable types
                return json.dumps(data, default=str)
            else:
                return json.dumps({"error": tool_result.error or "Unknown error"})
        except (TypeError, ValueError) as e:
            logger.warning("tool_result_serialization_failed", error=str(e))
            return json.dumps({
                "error": "Failed to serialize tool result",
                "details": str(tool_result.data)[:500]
            })

    async def _run_worker_llm(
            self,
            system_prompt: str,
            context: Dict[str, Any],
            user_id: str
    ) -> str:
        """
        Run the worker's LLM reasoning with timeout protection

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

        try:
            # Call LLM with timeout protection
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=Config.CHAT_MODEL,
                    messages=messages,
                    tools=worker_tools if worker_tools else None,
                    tool_choice="auto" if worker_tools else None,
                    temperature=0.3,
                    max_tokens=4000,
                    timeout=120.0  # OpenAI client timeout
                ),
                timeout=150.0  # Overall operation timeout
            )
        except asyncio.TimeoutError:
            logger.error("worker_llm_timeout",
                        worker_type=self.worker_type.value,
                        user_id=user_id)
            raise ValueError("LLM request timed out after 150 seconds")

        # Handle tool calls if present
        assistant_message = response.choices[0].message

        if assistant_message.tool_calls:
            # Execute tools and continue conversation
            messages.append({
                "role": "assistant",
                "content": assistant_message.content or "",  # Ensure string
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
                try:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError as e:
                    logger.error(
                        "tool_args_parse_error",
                        tool_name=tool_call.function.name,
                        error=str(e)
                    )
                    # Add error message for this tool call
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.function.name,
                        "content": json.dumps({"error": f"Failed to parse arguments: {str(e)}"})
                    })
                    continue

                tool_result = await self.tool_executor.execute(
                    tool_name,
                    tool_args,
                    user_id
                )

                # Store tool result in context with error handling
                try:
                    self.context_store.add_tool_result(tool_name, tool_result)
                except Exception as e:
                    logger.warning("failed_to_store_tool_result",
                                  tool_name=tool_name,
                                  error=str(e))

                # Safely serialize tool result
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": self._serialize_tool_result(tool_result)
                })

            # Get final response with tool results
            try:
                final_response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=Config.CHAT_MODEL,
                        messages=messages,
                        temperature=0.3,
                        max_tokens=4000,
                        timeout=120.0
                    ),
                    timeout=150.0
                )
            except asyncio.TimeoutError:
                logger.error("worker_final_response_timeout",
                            worker_type=self.worker_type.value)
                raise ValueError("Final LLM request timed out")

            final_content = final_response.choices[0].message.content
            return final_content if final_content else ""

        return assistant_message.content or ""

    @staticmethod
    def _format_other_insights(insights: List[Dict[str, Any]]) -> str:
        """Format insights from other workers"""
        if not insights:
            return "No prior insights available."

        formatted = []
        for insight in insights:
            formatted.append(
                f"- {insight.get('from_worker', 'Unknown')}: {insight.get('summary', '')} "
                f"(confidence: {insight.get('confidence', 0.0):.2f})"
            )

        return "\n".join(formatted)

    def _empty_structured_response(self) -> Dict[str, Any]:
        """Return empty structured response"""
        return {
            "data": {
                "full_analysis": "",
                "worker_type": self.worker_type.value,
                "key_points": []
            },
            "recommendations": [],
            "confidence": 0.0,
            "sources": []
        }

    def _structure_response(self, response: str) -> Dict[str, Any]:
        """
        Parse and structure the LLM response

        Args:
            response: Raw LLM response text

        Returns:
            Structured dictionary with data, recommendations, etc.
        """
        # Validate and truncate input
        if not response or not isinstance(response, str):
            return self._empty_structured_response()

        # Truncate extremely long responses to prevent regex issues
        if len(response) > 50000:
            logger.warning("truncating_long_response",
                          worker_type=self.worker_type.value,
                          original_length=len(response))
            response = response[:50000]

        # Extract recommendations with safer line-by-line parsing
        recommendations = []
        lines = response.split('\n')
        current_rec = None

        for line in lines:
            # Match numbered list items
            match = re.match(r'^\s*(\d+)\.\s+(.+)$', line)
            if match:
                # Save previous recommendation if exists
                if current_rec and len(current_rec) > 10:
                    recommendations.append(current_rec)
                current_rec = match.group(2).strip()
            elif current_rec and line.strip() and not re.match(r'^\s*\d+\.', line):
                # Continue current recommendation (multiline)
                if len(current_rec) < 500:  # Prevent runaway concatenation
                    current_rec += " " + line.strip()
            elif current_rec:
                # Empty line or new section - save current
                if len(current_rec) > 10:
                    recommendations.append(current_rec)
                current_rec = None

        # Save last recommendation
        if current_rec and len(current_rec) > 10:
            recommendations.append(current_rec)

        # Extract confidence with better validation
        confidence = 0.8  # Default
        conf_pattern = r'confidence[:\s]+([0-9]+\.?[0-9]*)'
        conf_match = re.search(conf_pattern, response.lower())
        if conf_match:
            try:
                conf_str = conf_match.group(1)
                # Validate it's a proper decimal
                if conf_str.count('.') <= 1:
                    confidence = float(conf_str)
                    # Normalize to 0.0-1.0 range
                    if confidence > 1.0:
                        confidence = min(confidence / 100.0, 1.0)
                    # Clamp to valid range
                    confidence = max(0.0, min(confidence, 1.0))
                else:
                    logger.warning("invalid_confidence_format", value=conf_str)
                    confidence = 0.8
            except (ValueError, OverflowError) as e:
                logger.warning("confidence_parse_failed",
                              raw_value=conf_match.group(1),
                              error=str(e))
                confidence = 0.8

        # Extract sources/references with better validation
        sources = []
        source_pattern = r'https?://[^\s)<>"\']+[^\s)<>"\',.]'
        potential_sources = re.findall(source_pattern, response)

        for url in potential_sources:
            # Clean up common trailing characters
            url = url.rstrip('.,;:!?)')
            # Basic validation
            if len(url) > 10 and '.' in url:
                sources.append(url)

        sources = list(set(sources))  # Remove duplicates

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

    @staticmethod
    def _extract_key_points(text: str) -> List[str]:
        """Extract bullet points or key statements"""
        if not text or not isinstance(text, str):
            return []

        # Truncate extremely long text
        if len(text) > 10000:
            text = text[:10000]

        key_points = []
        # Look for bullet points
        bullet_pattern = r'^[\s]*[•\-*]\s+(.+?)$'
        for line in text.split('\n'):
            match = re.match(bullet_pattern, line)
            if match:
                cleaned = re.sub(r'\s+', ' ', match.group(1).strip())
                if len(cleaned) > 10:
                    key_points.append(cleaned)

        # If no bullets found, extract sentences with strong keywords
        if not key_points:
            strong_keywords = [
                'important', 'critical', 'recommend', 'should', 'must',
                'key', 'essential', 'crucial', 'significant', 'note that'
            ]
            # Compile keyword pattern once for efficiency
            keyword_pattern = re.compile('|'.join(re.escape(k) for k in strong_keywords), re.IGNORECASE)

            # Split by sentence-ending punctuation
            sentences = re.split(r'[.!?]+', text)
            for sentence in sentences[:100]:  # Limit iterations to prevent slowdown
                if keyword_pattern.search(sentence):
                    clean = sentence.strip()
                    if 20 <= len(clean) <= 200:
                        key_points.append(clean)

        # Remove duplicates while preserving order
        seen = set()
        unique_points = []
        for point in key_points:
            point_lower = point.lower()
            if point_lower not in seen:
                seen.add(point_lower)
                unique_points.append(point)

        return unique_points[:5]  # Limit to top 5
