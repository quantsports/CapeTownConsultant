"""
Vector memory system using Pinecone
Stores and retrieves memories using semantic search with enhanced reliability
"""

import hashlib
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional

from pinecone import Pinecone, ServerlessSpec

from src.config.settings import Config
from src.core.models import ToolResult
from src.core.logging import logger
from src.services.embeddings import EmbeddingService


class VectorMemory:
    """Pinecone-based vector memory system with retry logic and validation"""

    def __init__(
            self,
            embedding_service: EmbeddingService,
            api_key: Optional[str] = None,
            region: Optional[str] = None
    ):
        self.embedding_service = embedding_service
        self.api_key = api_key or Config.PINECONE_API_KEY
        self.index_name = Config.PINECONE_INDEX
        self.region = region or getattr(Config, 'PINECONE_REGION', 'us-east-1')

        # Lazy initialization
        self.pc: Optional[Pinecone] = None
        self.index = None
        self._initialized = False
        self._init_lock = asyncio.Lock()

        # Batch limits
        self.max_batch_size = 100  # Pinecone recommendation

        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds

    def is_configured(self) -> bool:
        """Check if Pinecone is configured"""
        return self.api_key is not None and self.api_key != ""

    async def _ensure_initialized(self):
        """Lazy initialization with thread safety"""
        if self._initialized:
            return

        async with self._init_lock:
            # Double-check after acquiring a lock
            if self._initialized:
                return

            if not self.is_configured():
                logger.warning("pinecone_not_configured")
                return

            try:
                # Initialize in the executor to avoid blocking
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._sync_initialize
                )
                self._initialized = True
                logger.info("pinecone_initialized", index=self.index_name)
            except Exception as e:
                logger.error("pinecone_initialization_failed", error=str(e))
                raise

    def _sync_initialize(self):
        """Synchronous initialization (runs in executor)"""
        self.pc = Pinecone(api_key=self.api_key)
        self._ensure_index()
        self.index = self.pc.Index(self.index_name)

    def _ensure_index(self):
        """Create a Pinecone index if it doesn't exist"""
        try:
            existing_indexes = self.pc.list_indexes().names()
            if self.index_name not in existing_indexes:
                logger.info("creating_pinecone_index", index=self.index_name)
                self.pc.create_index(
                    name=self.index_name,
                    dimension=Config.PINECONE_DIMENSION,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region=self.region)
                )
                logger.info("pinecone_index_created", index=self.index_name)
        except Exception as e:
            logger.error("pinecone_index_setup_failed", error=str(e))
            raise

    async def health_check(self) -> bool:
        """Check if Pinecone connection is healthy"""
        try:
            await self._ensure_initialized()
            if not self.index:
                return False

            # Test with a simple stats call
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.index.describe_index_stats()
            )
            return True
        except Exception as e:
            logger.error("health_check_failed", error=str(e))
            return False

    def _validate_namespace(self, namespace: str) -> bool:
        """Validate namespace format"""
        if not namespace or not isinstance(namespace, str):
            return False

        # Pinecone namespace requirements
        if len(namespace) > 512:
            return False

        return True

    async def _retry_operation(self, operation, *args, **kwargs):
        """Retry operation with exponential backoff"""
        last_error = None

        for attempt in range(self.max_retries):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning("operation_retry",
                                   attempt=attempt + 1,
                                   delay=delay,
                                   error=str(e))
                    await asyncio.sleep(delay)
                else:
                    logger.error("operation_failed_after_retries",
                                 error=str(e),
                                 attempts=self.max_retries)

        raise last_error

    async def query(
            self,
            text: str,
            namespace: str,
            top_k: int = 5,
            filter_dict: Optional[Dict] = None,
            user_id: str = "default"
    ) -> ToolResult:
        """Query vector memory with retry logic"""
        # Validate inputs
        if not text or not isinstance(text, str) or not text.strip():
            return ToolResult(
                success=False,
                error="Query text cannot be empty",
                source="vector_memory"
            )

        if not self._validate_namespace(namespace):
            return ToolResult(
                success=False,
                error="Invalid namespace format",
                source="vector_memory"
            )

        # Clamp top_k
        top_k = max(1, min(top_k, 100))

        try:
            await self._ensure_initialized()

            if not self.index:
                return ToolResult(
                    success=False,
                    error="Pinecone not configured",
                    source="vector_memory"
                )

            # Execute query with retry
            result = await self._retry_operation(
                self._execute_query,
                text,
                namespace,
                top_k,
                filter_dict,
                user_id
            )

            return result

        except Exception as e:
            logger.error("memory_query_failed", error=str(e), user_id=user_id)
            return ToolResult(
                success=False,
                error=f"Query failed: {str(e)}",
                source="vector_memory"
            )

    async def _execute_query(
            self,
            text: str,
            namespace: str,
            top_k: int,
            filter_dict: Optional[Dict],
            user_id: str
    ) -> ToolResult:
        """Internal query execution"""
        # Generate embedding
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

        # Execute query in executor
        results = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.index.query(**query_params)
        )

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

        logger.info("memory_query_success",
                    user_id=user_id,
                    namespace=namespace,
                    matches=len(matches))

        return ToolResult(
            success=True,
            data={"matches": matches, "namespace": namespace, "total": len(matches)},
            source="vector_memory"
        )

    async def upsert(
            self,
            items: List[Dict],
            namespace: str,
            user_id: str = "default"
    ) -> ToolResult:
        """Store items in vector memory with batching and retry"""
        # Validate inputs
        if not items or not isinstance(items, list):
            return ToolResult(
                success=False,
                error="Items must be a non-empty list",
                source="vector_memory"
            )

        if not self._validate_namespace(namespace):
            return ToolResult(
                success=False,
                error="Invalid namespace format",
                source="vector_memory"
            )

        try:
            await self._ensure_initialized()

            if not self.index:
                return ToolResult(
                    success=False,
                    error="Pinecone not configured",
                    source="vector_memory"
                )

            # Process in batches
            total_stored = 0
            for i in range(0, len(items), self.max_batch_size):
                batch = items[i:i + self.max_batch_size]

                result = await self._retry_operation(
                    self._execute_upsert_batch,
                    batch,
                    namespace,
                    user_id
                )

                if not result.success:
                    return result

                total_stored += result.data.get("stored", 0)

            logger.info("memory_upsert_complete",
                        total_stored=total_stored,
                        namespace=namespace,
                        user_id=user_id)

            return ToolResult(
                success=True,
                data={"stored": total_stored, "namespace": namespace},
                source="vector_memory"
            )

        except Exception as e:
            logger.error("memory_upsert_failed", error=str(e), user_id=user_id)
            return ToolResult(
                success=False,
                error=f"Upsert failed: {str(e)}",
                source="vector_memory"
            )

    async def _execute_upsert_batch(
            self,
            items: List[Dict],
            namespace: str,
            user_id: str
    ) -> ToolResult:
        """Internal batch upsert execution"""
        vectors = []
        texts = [item["text"] for item in items]

        # Generate embeddings in batch
        embeddings = await self.embedding_service.embed_batch(texts, user_id)
        timestamp = datetime.now(timezone.utc).isoformat()

        # Prepare vectors for upsert
        for item, embedding in zip(items, embeddings):
            vector_id = hashlib.md5(
                f"{item['text']}{timestamp}{user_id}".encode()
            ).hexdigest()

            metadata = item.get("meta", {})
            metadata.update({
                "text": item["text"],
                "timestamp": timestamp,
                "user_id": user_id
            })

            vectors.append({
                "id": vector_id,
                "values": embedding,
                "metadata": metadata
            })

        # Upsert to Pinecone in executor
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.index.upsert(vectors=vectors, namespace=namespace)
        )

        logger.info("memory_batch_upserted",
                    count=len(vectors),
                    namespace=namespace)

        return ToolResult(
            success=True,
            data={"stored": len(vectors)},
            source="vector_memory"
        )

    async def delete_namespace(self, namespace: str) -> bool:
        """Delete all vectors in a namespace"""
        try:
            await self._ensure_initialized()

            if not self.index:
                return False

            if not self._validate_namespace(namespace):
                logger.warning("invalid_namespace_delete", namespace=namespace)
                return False

            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.index.delete(delete_all=True, namespace=namespace)
            )

            logger.info("namespace_deleted", namespace=namespace)
            return True

        except Exception as e:
            logger.error("namespace_delete_failed", namespace=namespace, error=str(e))
            return False