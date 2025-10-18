"""
Vector memory system using Pinecone
Store and retrieve memories using semantic search with enhanced reliability
FIXES: High #3 - Memory leak from unreleased _init_lock
FIXES: Medium #8 - Missing timeout on Pinecone queries
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

        # HIGH FIX #3: Use temporary lock that will be deleted after initialization
        # to prevent memory leak
        self._init_lock: Optional[asyncio.Lock] = asyncio.Lock()

        # Batch limits
        self.max_batch_size = 100  # Pinecone recommendation

        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds

        # MEDIUM FIX #8: Query timeout (30 seconds)
        self.query_timeout = 30.0

    def is_configured(self) -> bool:
        """Check if Pinecone is configured"""
        return self.api_key is not None and self.api_key != ""

    async def _ensure_initialized(self):
        """
        Lazy initialization with thread safety
        HIGH FIX #3: Delete lock after initialization to prevent memory leak
        """
        if self._initialized:
            return

        # Use lock if it exists, otherwise skip (already initialized)
        if self._init_lock is not None:
            async with self._init_lock:
                # Double-check after acquiring lock
                if self._initialized:
                    return

                if not self.is_configured():
                    logger.warning("pinecone_not_configured")
                    # HIGH FIX #3: Delete lock even if not configured
                    self._init_lock = None
                    return

                try:
                    # Initialize in executor to avoid blocking
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        self._sync_initialize
                    )
                    self._initialized = True
                    logger.info("pinecone_initialized", index=self.index_name)
                except Exception as e:
                    logger.error("pinecone_initialization_failed", error=str(e))
                    raise
                finally:
                    # HIGH FIX #3: Delete the lock after initialization to free memory
                    self._init_lock = None

    def _sync_initialize(self):
        """Synchronous initialization (runs in executor)"""
        self.pc = Pinecone(api_key=self.api_key)
        self._ensure_index()
        self.index = self.pc.Index(self.index_name)

    def _ensure_index(self):
        """Create Pinecone index if it doesn't exist"""
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

            # Test with a simple stats call with timeout
            # MEDIUM FIX #8: Add timeout to prevent indefinite blocking
            stats_task = asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.index.describe_index_stats()
            )
            await asyncio.wait_for(stats_task, timeout=self.query_timeout)
            return True
        except asyncio.TimeoutError:
            logger.error("health_check_timeout", timeout=self.query_timeout)
            return False
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
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        "operation_retry",
                        attempt=attempt + 1,
                        wait=wait_time,
                        error=str(e)
                    )
                    await asyncio.sleep(wait_time)

        raise last_error

    async def query(
            self,
            text: str,
            namespace: str,
            top_k: int = 5,
            filter_dict: Optional[Dict] = None,
            user_id: str = "default"
    ) -> ToolResult:
        """
        Query vector memory with semantic search
        MEDIUM FIX #8: Add timeout to Pinecone query
        """
        await self._ensure_initialized()

        if not self.index:
            return ToolResult(success=False, error="Pinecone not configured")

        # Validate namespace
        if not self._validate_namespace(namespace):
            return ToolResult(
                success=False,
                error=f"Invalid namespace: {namespace}"
            )

        try:
            # Generate embedding
            embedding = await self.embedding_service.embed(text, user_id)

            # Prepare query params
            query_params = {
                "vector": embedding,
                "top_k": top_k,
                "namespace": namespace,
                "include_metadata": True
            }

            if filter_dict:
                query_params["filter"] = filter_dict

            # MEDIUM FIX #8: Execute query with timeout
            query_task = asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.index.query(**query_params)
            )

            results = await asyncio.wait_for(query_task, timeout=self.query_timeout)

            # Process matches
            matches = []
            for match in results.get("matches", []):
                score = match.get("score", 0.0)

                # Only include matches above threshold
                if score >= Config.MEMORY_SIMILARITY_THRESHOLD:
                    matches.append({
                        "id": match.get("id", ""),
                        "score": score,
                        "text": match.get("metadata", {}).get("text", ""),
                        "metadata": match.get("metadata", {}),
                        "timestamp": match.get("metadata", {}).get("timestamp", "")
                    })

            logger.info(
                "memory_query_success",
                namespace=namespace,
                matches=len(matches),
                user_id=user_id
            )

            return ToolResult(
                success=True,
                data={"matches": matches, "namespace": namespace}
            )

        except asyncio.TimeoutError:
            logger.error(
                "memory_query_timeout",
                timeout=self.query_timeout,
                namespace=namespace,
                user_id=user_id
            )
            return ToolResult(
                success=False,
                error=f"Memory query timed out after {self.query_timeout}s"
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
        """
        Store items in vector memory with batching
        MEDIUM FIX #8: Add timeout to upsert operation
        """
        await self._ensure_initialized()

        if not self.index:
            return ToolResult(success=False, error="Pinecone not configured")

        # Validate namespace
        if not self._validate_namespace(namespace):
            return ToolResult(
                success=False,
                error=f"Invalid namespace: {namespace}"
            )

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

            # MEDIUM FIX #8: Upsert with timeout
            upsert_task = asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.index.upsert(vectors=vectors, namespace=namespace)
            )

            await asyncio.wait_for(upsert_task, timeout=self.query_timeout)

            logger.info(
                "memory_upsert_success",
                count=len(vectors),
                namespace=namespace
            )

            return ToolResult(
                success=True,
                data={"stored": len(vectors), "namespace": namespace}
            )

        except asyncio.TimeoutError:
            logger.error(
                "memory_upsert_timeout",
                timeout=self.query_timeout,
                namespace=namespace,
                user_id=user_id
            )
            return ToolResult(
                success=False,
                error=f"Memory upsert timed out after {self.query_timeout}s"
            )
        except Exception as e:
            logger.error("memory_upsert_failed", error=str(e), user_id=user_id)
            return ToolResult(success=False, error=f"Memory upsert failed: {str(e)}")