"""
Unified memory system
Combines vector memory and user profiles
"""

from datetime import datetime
from typing import Any, Dict

from src.memory.vector import VectorMemory
from src.memory.profile import ProfileManager


class UnifiedMemorySystem:
    """Integrated profile and vector memory"""

    def __init__(
        self,
        vector_memory: VectorMemory,
        profile_manager: ProfileManager
    ):
        self.vector_memory = vector_memory
        self.profile_manager = profile_manager

    async def get_context(self, user_id: str, query: str) -> Dict[str, Any]:
        """Get full context for user query"""
        # Read user profile
        profile = await self.profile_manager.read(user_id)

        # Query vector memory
        namespace = f"user:{user_id}"
        memory_result = await self.vector_memory.query(
            query,
            namespace,
            top_k=5,
            user_id=user_id
        )

        # Extract memories
        memories = []
        if memory_result.success:
            memories = memory_result.data.get("matches", [])

        return {
            "profile": profile,
            "memories": memories,
            "timestamp": datetime.now().isoformat()
        }

    async def store_memory(
        self,
        user_id: str,
        text: str,
        metadata: Dict = None
    ) -> bool:
        """Store a single memory"""
        namespace = f"user:{user_id}"
        items = [{
            "text": text,
            "meta": metadata or {}
        }]

        result = await self.vector_memory.upsert(items, namespace, user_id)
        return result.success

    async def update_profile(self, user_id: str, data: Dict) -> bool:
        """Update user profile"""
        return await self.profile_manager.write(user_id, data)