"""
Unified memory system
Combines vector memory and user profiles with enhanced reliability
"""

from datetime import datetime
from typing import Any, Dict, Optional, List
import asyncio

from src.memory.vector import VectorMemory
from src.memory.profile import ProfileManager
from src.core.logging import logger


class UnifiedMemorySystem:
    """Integrated profile and vector memory with error handling"""

    def __init__(
        self,
        vector_memory: VectorMemory,
        profile_manager: ProfileManager
    ):
        self.vector_memory = vector_memory
        self.profile_manager = profile_manager

        # Metrics
        self._context_retrieval_count = 0
        self._memory_store_count = 0
        self._profile_update_count = 0

    def is_configured(self) -> bool:
        """Check if memory system is properly configured"""
        return (
            self.vector_memory is not None and
            self.profile_manager is not None and
            self.vector_memory.is_configured()
        )

    @staticmethod
    def _validate_namespace(user_id: str) -> str:
        """Validate and format namespace"""
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")

        # Sanitize user_id for namespace
        safe_id = user_id.strip().replace(" ", "_")
        if not safe_id:
            raise ValueError("user_id cannot be empty after sanitization")

        return f"user:{safe_id}"

    async def get_context(
        self,
        user_id: str,
        query: str,
        memory_top_k: int = 5,
        timeout: float = 10.0
    ) -> Dict[str, Any]:
        """
        Get full context for user query with error handling

        Args:
            user_id: User identifier
            query: Query text for memory search
            memory_top_k: Number of memory results to retrieve
            timeout: Operation timeout in seconds

        Returns:
            Dictionary with profile, memories, and metadata
        """
        self._context_retrieval_count += 1

        # Validate inputs
        if not query or not isinstance(query, str):
            logger.warning("invalid_query", user_id=user_id)
            query = ""  # Use empty query, will just get profile

        try:
            # Validate namespace
            namespace = self._validate_namespace(user_id)
        except ValueError as e:
            logger.error("invalid_user_id", user_id=user_id, error=str(e))
            return {
                "profile": {},
                "memories": [],
                "timestamp": datetime.now().isoformat(),
                "errors": [f"Invalid user_id: {e}"]
            }

        errors = []
        profile = {}
        memories = []

        # Retrieve profile with timeout
        try:
            profile = await asyncio.wait_for(
                self.profile_manager.read(user_id),
                timeout=timeout / 2
            )
        except asyncio.TimeoutError:
            error_msg = "Profile retrieval timed out"
            logger.warning("profile_retrieval_timeout", user_id=user_id)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Profile retrieval failed: {str(e)}"
            logger.error("profile_retrieval_failed", user_id=user_id, error=str(e))
            errors.append(error_msg)

        # Query vector memory if query provided
        if query.strip():
            try:
                memory_result = await asyncio.wait_for(
                    self.vector_memory.query(
                        query,
                        namespace,
                        top_k=memory_top_k,
                        user_id=user_id
                    ),
                    timeout=timeout / 2
                )

                if memory_result.success:
                    memories = memory_result.data.get("matches", [])
                    logger.info("memory_query_success",
                               user_id=user_id,
                               matches=len(memories))
                else:
                    error_msg = f"Memory query failed: {memory_result.error}"
                    logger.warning("memory_query_failed",
                                  user_id=user_id,
                                  error=memory_result.error)
                    errors.append(error_msg)

            except asyncio.TimeoutError:
                error_msg = "Memory query timed out"
                logger.warning("memory_query_timeout", user_id=user_id)
                errors.append(error_msg)
            except Exception as e:
                error_msg = f"Memory query failed: {str(e)}"
                logger.error("memory_query_exception", user_id=user_id, error=str(e))
                errors.append(error_msg)

        result = {
            "profile": profile,
            "memories": memories,
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "memory_count": len(memories)
        }

        if errors:
            result["errors"] = errors

        return result

    async def store_memory(
        self,
        user_id: str,
        text: str,
        metadata: Optional[Dict] = None,
        timeout: float = 10.0
    ) -> bool:
        """
        Store a single memory with validation

        Args:
            user_id: User identifier
            text: Memory text to store
            metadata: Optional metadata dict
            timeout: Operation timeout in seconds

        Returns:
            True if successful, False otherwise
        """
        self._memory_store_count += 1

        # Validate inputs
        if not text or not isinstance(text, str):
            logger.warning("invalid_memory_text", user_id=user_id)
            return False

        if not text.strip():
            logger.warning("empty_memory_text", user_id=user_id)
            return False

        # Validate metadata
        if metadata is not None and not isinstance(metadata, dict):
            logger.warning("invalid_metadata", user_id=user_id)
            metadata = {}

        try:
            namespace = self._validate_namespace(user_id)
        except ValueError as e:
            logger.error("invalid_user_id", user_id=user_id, error=str(e))
            return False

        try:
            items = [{
                "text": text.strip(),
                "meta": metadata or {}
            }]

            result = await asyncio.wait_for(
                self.vector_memory.upsert(items, namespace, user_id),
                timeout=timeout
            )

            if result.success:
                logger.info("memory_stored", user_id=user_id)
                return True
            else:
                logger.warning("memory_store_failed",
                              user_id=user_id,
                              error=result.error)
                return False

        except asyncio.TimeoutError:
            logger.error("memory_store_timeout", user_id=user_id)
            return False
        except Exception as e:
            logger.error("memory_store_exception", user_id=user_id, error=str(e))
            return False

    async def store_memories_batch(
        self,
        user_id: str,
        items: List[Dict],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Store multiple memories in batch

        Args:
            user_id: User identifier
            items: List of dicts with 'text' and optional 'meta' fields
            timeout: Operation timeout in seconds

        Returns:
            Dict with success status and metrics
        """
        if not items or not isinstance(items, list):
            logger.warning("invalid_items_list", user_id=user_id)
            return {"success": False, "error": "Invalid items list", "stored": 0}

        # Validate each item
        valid_items = []
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                logger.warning("invalid_item_format", user_id=user_id, index=i)
                continue

            if "text" not in item or not item["text"] or not item["text"].strip():
                logger.warning("invalid_item_text", user_id=user_id, index=i)
                continue

            valid_items.append({
                "text": item["text"].strip(),
                "meta": item.get("meta", {})
            })

        if not valid_items:
            logger.warning("no_valid_items", user_id=user_id)
            return {"success": False, "error": "No valid items", "stored": 0}

        try:
            namespace = self._validate_namespace(user_id)

            result = await asyncio.wait_for(
                self.vector_memory.upsert(valid_items, namespace, user_id),
                timeout=timeout
            )

            if result.success:
                logger.info("memories_batch_stored",
                           user_id=user_id,
                           count=len(valid_items))
                return {
                    "success": True,
                    "stored": len(valid_items),
                    "skipped": len(items) - len(valid_items)
                }
            else:
                return {
                    "success": False,
                    "error": result.error,
                    "stored": 0
                }

        except asyncio.TimeoutError:
            logger.error("memories_batch_timeout", user_id=user_id)
            return {"success": False, "error": "Operation timed out", "stored": 0}
        except Exception as e:
            logger.error("memories_batch_exception", user_id=user_id, error=str(e))
            return {"success": False, "error": str(e), "stored": 0}

    async def update_profile(
        self,
        user_id: str,
        data: Dict,
        timeout: float = 5.0
    ) -> bool:
        """
        Update user profile with validation

        Args:
            user_id: User identifier
            data: Profile data to update
            timeout: Operation timeout in seconds

        Returns:
            True if successful, False otherwise
        """
        self._profile_update_count += 1

        # Validate inputs
        if not data or not isinstance(data, dict):
            logger.warning("invalid_profile_data", user_id=user_id)
            return False

        try:
            result = await asyncio.wait_for(
                self.profile_manager.write(user_id, data),
                timeout=timeout
            )

            if result:
                logger.info("profile_updated", user_id=user_id, keys=list(data.keys()))
            else:
                logger.warning("profile_update_failed", user_id=user_id)

            return result

        except asyncio.TimeoutError:
            logger.error("profile_update_timeout", user_id=user_id)
            return False
        except Exception as e:
            logger.error("profile_update_exception", user_id=user_id, error=str(e))
            return False

    def get_metrics(self) -> Dict[str, int]:
        """Get usage metrics"""
        return {
            "context_retrievals": self._context_retrieval_count,
            "memories_stored": self._memory_store_count,
            "profile_updates": self._profile_update_count
        }

    def reset_metrics(self):
        """Reset usage metrics"""
        self._context_retrieval_count = 0
        self._memory_store_count = 0
        self._profile_update_count = 0