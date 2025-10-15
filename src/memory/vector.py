"""
Vector memory system using Pinecone
Store and retrieve memories using semantic search
"""

import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional

from pinecone import Pinecone, ServerlessSpec

from src.config.settings import Config
from src.core.models import ToolResult
from src.core.logging import logger
from src.services.embeddings import EmbeddingService


class VectorMemory:
    """Pinecone-based vector memory system"""

    def __init__(
            self,
            embedding_service: EmbeddingService,
            api_key: Optional[str] = None
    ):
        self.embedding_service = embedding_service
        self.api_key = api_key or Config.PINECONE_API_KEY
        self.index_name = Config.PINECONE_INDEX

        if self.api_key:
            self.pc = Pinecone(api_key=self.api_key)
            self._ensure_index()
            self.index = self.pc.Index(self.index_name)
        else:
            self.pc = None
            self.index = None

    def _ensure_index(self):
        """Create Pinecone index if it doesn't exist"""
        try:
            existing_indexes = self.pc.list_indexes().names()
            if self.index_name not in existing_indexes:
                self.pc.create_index(
                    name=self.index_name,
                    dimension=Config.PINECONE_DIMENSION,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1")
                )
                logger.info("pinecone_index_created", index=self.index_name)
        except Exception as e:
            logger.warning("pinecone_index_setup_failed", error=str(e))

    async def query(
            self,
            text: str,
            namespace: str,
            top_k: int = 5,
            filter_dict: Optional[Dict] = None,
            user_id: str = "default"
    ) -> ToolResult:
        """Query vector memory"""
        if not self.index:
            return ToolResult(success=False, error="Pinecone not configured")

        try:
            # Generate embedding for query
            embedding = await self.embedding_service.embed(text, user_id)

            # Prepare query parameters
            query_params = {
                "vector": embedding,
                "top_k": top_k,
                "namespace": namespace,
                "include_metadata": True
            }

            if filter_dict:
                query_params["filter"] = filter_dict

            # Execute query
            results = self.index.query(**query_params)

            # Filter by similarity threshold
            matches = []
            for match in results.get("matches", []):
                score = match.get("score", 0.0)
                if score >= Config.MEMORY_SIMILARITY_THRESHOLD:
                    matches.append({
                        "id": match.get("id", ""),
                        "score": score,
                        "text": match.get("metadata", {}).get("text", ""),
                        "metadata": match.get("metadata", {}),
                        "timestamp": match.get("metadata", {}).get("timestamp", "")
                    })

            return ToolResult(
                success=True,
                data={"matches": matches, "namespace": namespace}
            )

        except Exception as e:
            logger.error("memory_query_failed", error=str(e), user_id=user_id)
            return ToolResult(success=False, error=f"Memory query failed: {str(e)}")

    async def upsert(
            self,
            items: List[Dict],
            namespace: str,
            user_id: str = "default"
    ) -> ToolResult:
        """Store items in vector memory"""
        if not self.index:
            return ToolResult(success=False, error="Pinecone not configured")

        try:
            vectors = []
            texts = [item["text"] for item in items]

            # Generate embeddings in batch
            embeddings = await self.embedding_service.embed_batch(texts, user_id)
            timestamp = datetime.now(timezone.utc).isoformat()

            # Prepare vectors for upsert
            for item, embedding in zip(items, embeddings):
                vector_id = hashlib.md5(
                    f"{item['text']}{timestamp}".encode()
                ).hexdigest()

                metadata = item.get("meta", {})
                metadata.update({
                    "text": item["text"],
                    "timestamp": timestamp
                })

                vectors.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": metadata
                })

            # Upsert to Pinecone
            self.index.upsert(vectors=vectors, namespace=namespace)

            logger.info(
                "memory_upsert_success",
                count=len(vectors),
                namespace=namespace
            )

            return ToolResult(
                success=True,
                data={"stored": len(vectors), "namespace": namespace}
            )

        except Exception as e:
            logger.error("memory_upsert_failed", error=str(e), user_id=user_id)
            return ToolResult(success=False, error=f"Memory upsert failed: {str(e)}")