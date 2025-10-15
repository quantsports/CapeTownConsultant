"""
Autonomous Personal Assistant - Production Ready (Enhanced & Fixed)
Fixes Applied: Issues 1, 2, 3, 4, 6, 7, 8, 9, 10
Backward Compatible - All original functionality preserved
"""

import json
import os
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Literal, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import httpx
from collections import OrderedDict
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
import sys
from loguru import logger as _loguru_logger

load_dotenv(find_dotenv())

# External dependencies
try:
    from openai import AsyncOpenAI
    from pinecone import Pinecone, ServerlessSpec
    from tenacity import retry, stop_after_attempt, wait_exponential
    import aiofiles
    import aiolimiter
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install: pip install openai pinecone-client pydantic tenacity httpx aiofiles aiolimiter structlog")

# ============================================================================
# LOGGING SETUP (Loguru)
# ============================================================================
# Balanced, simple logger: console + rotating file; respects LOG_LEVEL env
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Reset default sinks and configure ours
_loguru_logger.remove()

# Ensure log directory exists
_log_dir = Path("./cache/logs")
_log_dir.mkdir(parents=True, exist_ok=True)

# Console sink (colorized)
_loguru_logger.add(
    sys.stdout,
    level=LOG_LEVEL,
    enqueue=True,
    backtrace=False,
    diagnose=False,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level:<8}</level> | {message}"
)

# File sink (rotation + retention)
_loguru_logger.add(
    str(_log_dir / "app.log"),
    level=LOG_LEVEL,
    rotation="10 MB",
    retention="14 days",
    enqueue=True,
    backtrace=False,
    diagnose=False,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {message}"
)

class _KvLogger:
    """Adapter to support logger.info('event', key=value) style calls."""
    def __init__(self, base):
        self._base = base

    def _emit(self, level: str, event: str, **kwargs):
        if kwargs:
            parts = []
            for k, v in kwargs.items():
                try:
                    val = json.dumps(v, default=str)
                except Exception:
                    val = str(v)
                parts.append(f"{k}={val}")
            msg = f"{event} | " + " ".join(parts)
        else:
            msg = event
        self._base.log(level.upper(), msg)

    def debug(self, event: str, **kwargs): self._emit("DEBUG", event, **kwargs)
    def info(self, event: str, **kwargs): self._emit("INFO", event, **kwargs)
    def warning(self, event: str, **kwargs): self._emit("WARNING", event, **kwargs)
    def error(self, event: str, **kwargs): self._emit("ERROR", event, **kwargs)

    def bind(self, **kwargs):
        return _KvLogger(self._base.bind(**kwargs))

logger = _KvLogger(_loguru_logger)


# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Centralized configuration"""
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
    GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY")
    GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

    PINECONE_INDEX = "assistant-memory"
    PINECONE_DIMENSION = 1536
    EMBEDDING_MODEL = "text-embedding-3-small"
    CHAT_MODEL = "gpt-4o"
    SUMMARY_MODEL = "gpt-4o-mini"

    MAX_RETRIES = 2
    TIMEOUT_SECONDS = 30
    MAX_CONVERSATION_HISTORY = 20
    CACHE_MAX_SIZE = 1000

    # Rate limiting (Fix #7)
    OPENAI_RPM = 50
    SERPAPI_RPM = 100
    PERPLEXITY_RPM = 20

    # Memory settings (Fix #1)
    MEMORY_SIMILARITY_THRESHOLD = 0.65
    AUTO_MEMORY_EXTRACTION = True

    # Cost tracking (Fix #2)
    ENABLE_COST_TRACKING = True
    DAILY_BUDGET_LIMIT = 5.0

    # Persistence
    PROFILE_DIR = "./data/profiles"
    CONVERSATION_DIR = "./data/conversations"
    CACHE_DIR = "./cache"
    EMBEDDING_CACHE_DIR = "./cache/embeddings"


# ============================================================================
# COST TRACKING SYSTEM (Fix #2)
# ============================================================================

class CostTracker:
    """Track and limit API costs per user"""

    COSTS = {
        "gpt-4o-input": 2.50 / 1_000_000,
        "gpt-4o-output": 10.00 / 1_000_000,
        "gpt-4o-mini-input": 0.15 / 1_000_000,
        "gpt-4o-mini-output": 0.60 / 1_000_000,
        "embedding": 0.02 / 1_000_000,
        "serpapi": 0.002,
        "perplexity": 0.001,
        "google-search": 0.005,
    }

    def __init__(self, storage_dir: str = None):
        self.storage_dir = Path(storage_dir or Config.CACHE_DIR) / "costs"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.user_costs: Dict[str, float] = {}
        self.daily_limits: Dict[str, float] = {}

    def _cost_file(self, user_id: str) -> Path:
        safe_id = hashlib.md5(user_id.encode()).hexdigest()
        today = datetime.now().strftime("%Y-%m-%d")
        return self.storage_dir / f"{safe_id}_{today}.json"

    async def load_user_costs(self, user_id: str):
        cost_file = self._cost_file(user_id)
        if cost_file.exists():
            try:
                async with aiofiles.open(cost_file, 'r') as f:
                    data = json.loads(await f.read())
                    self.user_costs[user_id] = data.get("total", 0.0)
            except Exception as e:
                logger.error("cost_load_failed", user_id=user_id, error=str(e))
                self.user_costs[user_id] = 0.0
        else:
            self.user_costs[user_id] = 0.0

    async def save_user_costs(self, user_id: str):
        cost_file = self._cost_file(user_id)
        try:
            async with aiofiles.open(cost_file, 'w') as f:
                await f.write(json.dumps({
                    "total": self.user_costs.get(user_id, 0.0),
                    "timestamp": datetime.now().isoformat()
                }))
        except Exception as e:
            logger.error("cost_save_failed", user_id=user_id, error=str(e))

    def estimate_cost(self, operation: str, units: int = 1) -> float:
        return self.COSTS.get(operation, 0.0) * units

    async def check_budget(self, user_id: str, operation: str, units: int = 1) -> bool:
        if not Config.ENABLE_COST_TRACKING:
            return True
        await self.load_user_costs(user_id)
        current = self.user_costs.get(user_id, 0.0)
        limit = self.daily_limits.get(user_id, Config.DAILY_BUDGET_LIMIT)
        estimated_cost = self.estimate_cost(operation, units)
        return (current + estimated_cost) < limit

    async def record_cost(self, user_id: str, operation: str, units: int = 1):
        if not Config.ENABLE_COST_TRACKING:
            return
        cost = self.estimate_cost(operation, units)
        self.user_costs[user_id] = self.user_costs.get(user_id, 0.0) + cost
        await self.save_user_costs(user_id)

    async def get_user_costs(self, user_id: str) -> Dict[str, float]:
        await self.load_user_costs(user_id)
        limit = self.daily_limits.get(user_id, Config.DAILY_BUDGET_LIMIT)
        return {
            "total": self.user_costs.get(user_id, 0.0),
            "limit": limit,
            "remaining": limit - self.user_costs.get(user_id, 0.0)
        }


# ============================================================================
# DATA MODELS
# ============================================================================

class ToolType(str, Enum):
    WEB_SEARCH = "web_search"
    PERPLEXITY_SEARCH = "perplexity_search"
    GOOGLE_SEARCH = "google_search"
    WIKI_FETCH = "wiki_fetch"
    MEMORY_QUERY = "memory_query"
    MEMORY_UPSERT = "memory_upsert"
    PROFILE_READ = "profile_read"
    PROFILE_WRITE = "profile_write"


@dataclass
class ToolResult:
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    citations: List[str] = field(default_factory=list)
    source: Optional[str] = None
    cost: float = 0.0


@dataclass
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


class CitationManager:
    def __init__(self):
        self.citations: List[str] = []
        self.citation_map: Dict[str, int] = {}

    def add_citation(self, url: str) -> int:
        if url in self.citation_map:
            return self.citation_map[url]
        self.citations.append(url)
        ref_num = len(self.citations)
        self.citation_map[url] = ref_num
        return ref_num

    def add_citations(self, urls: List[str]) -> List[int]:
        return [self.add_citation(url) for url in urls]

    def format_citations(self) -> str:
        if not self.citations:
            return ""
        section = "\n\n---\n\n**Sources:**\n"
        for i, url in enumerate(self.citations, 1):
            section += f"[{i}] {url}\n"
        return section

    def clear(self):
        self.citations.clear()
        self.citation_map.clear()


class LRUCache:
    def __init__(self, max_size: int = 1000):
        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size

    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def set(self, key: str, value: Any):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

    def clear(self):
        self.cache.clear()


# ============================================================================
# PERSISTENT EMBEDDING CACHE (Fix #9)
# ============================================================================

class PersistentEmbeddingCache:
    """Disk-backed embedding cache with memory layer"""

    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir or Config.EMBEDDING_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.memory_cache = LRUCache(max_size=1000)

    def _cache_key(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def _cache_file(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    async def get(self, text: str) -> Optional[List[float]]:
        key = self._cache_key(text)
        if cached := self.memory_cache.get(key):
            return cached
        cache_file = self._cache_file(key)
        if cache_file.exists():
            try:
                async with aiofiles.open(cache_file, 'r') as f:
                    data = json.loads(await f.read())
                    embedding = data["embedding"]
                    self.memory_cache.set(key, embedding)
                    return embedding
            except Exception:
                pass
        return None

    async def set(self, text: str, embedding: List[float]):
        key = self._cache_key(text)
        self.memory_cache.set(key, embedding)
        cache_file = self._cache_file(key)
        try:
            async with aiofiles.open(cache_file, 'w') as f:
                await f.write(json.dumps({
                    "embedding": embedding,
                    "timestamp": datetime.now().isoformat()
                }))
        except Exception:
            pass


# ============================================================================
# EMBEDDING SERVICE (Fix #9)
# ============================================================================

class EmbeddingService:
    def __init__(self, api_key: str = None, cost_tracker: CostTracker = None):
        self.api_key = api_key or Config.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
        self.cache = PersistentEmbeddingCache()
        self.cost_tracker = cost_tracker
        self._rate_limiter = None

    @property
    def rate_limiter(self):
        if self._rate_limiter is None:
            self._rate_limiter = aiolimiter.AsyncLimiter(Config.OPENAI_RPM, 60)
        return self._rate_limiter

    @retry(stop=stop_after_attempt(Config.MAX_RETRIES), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def embed(self, text: str, user_id: str = "default") -> List[float]:
        if not self.client:
            raise ValueError("OpenAI API key not configured")

        cached = await self.cache.get(text)
        if cached is not None:
            return cached

        if self.cost_tracker and not await self.cost_tracker.check_budget(user_id, "embedding", len(text)):
            raise ValueError("Daily budget limit exceeded")

        async with self.rate_limiter:
            try:
                response = await self.client.embeddings.create(
                    model=Config.EMBEDDING_MODEL,
                    input=text[:8000]
                )
                embedding = response.data[0].embedding
                await self.cache.set(text, embedding)
                if self.cost_tracker:
                    await self.cost_tracker.record_cost(user_id, "embedding", len(text))
                return embedding
            except Exception as e:
                raise Exception(f"Embedding generation failed: {str(e)}")

    async def embed_batch(self, texts: List[str], user_id: str = "default") -> List[List[float]]:
        if not self.client:
            raise ValueError("OpenAI API key not configured")

        results = []
        to_embed = []
        indices = []

        for i, text in enumerate(texts):
            cached = await self.cache.get(text)
            if cached is not None:
                results.append(cached)
            else:
                to_embed.append(text[:8000])
                indices.append(i)
                results.append(None)

        if to_embed:
            total_chars = sum(len(t) for t in to_embed)
            if self.cost_tracker and not await self.cost_tracker.check_budget(user_id, "embedding", total_chars):
                raise ValueError("Daily budget limit exceeded")

            async with self.rate_limiter:
                try:
                    response = await self.client.embeddings.create(
                        model=Config.EMBEDDING_MODEL,
                        input=to_embed
                    )
                    for idx, embedding_obj in zip(indices, response.data):
                        embedding = embedding_obj.embedding
                        results[idx] = embedding
                        await self.cache.set(texts[idx], embedding)

                    if self.cost_tracker:
                        await self.cost_tracker.record_cost(user_id, "embedding", total_chars)

                except Exception as e:
                    raise Exception(f"Batch embedding failed: {str(e)}")

        return results


# ============================================================================
# ASYNC WIKIPEDIA SEARCH (Fix #3)
# ============================================================================

class AsyncWikipediaSearch:
    def __init__(self, http_client: httpx.AsyncClient):
        self.http_client = http_client
        self.base_url = "https://en.wikipedia.org/w/api.php"

    async def search(self, query: str, limit: int = 3) -> List[str]:
        params = {
            "action": "opensearch",
            "search": query,
            "limit": limit,
            "format": "json"
        }
        try:
            response = await self.http_client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data[1][:limit]
        except Exception:
            return []

    async def get_page_summary(self, title: str) -> Optional[Dict[str, str]]:
        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts|info",
            "exintro": True,
            "explaintext": True,
            "inprop": "url",
            "format": "json"
        }
        try:
            response = await self.http_client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            pages = data.get("query", {}).get("pages", {})
            for page_id, page in pages.items():
                if page_id != "-1":
                    extract = page.get("extract", "")
                    return {
                        "title": page.get("title", title),
                        "url": page.get("fullurl", ""),
                        "extract": extract[:500] + ("..." if len(extract) > 500 else "")
                    }
        except Exception:
            pass
        return None


# ============================================================================
# SEARCH ENGINES (Fix #2, #3)
# ============================================================================

class SearchEngine:
    def __init__(self, cost_tracker: CostTracker = None):
        self.serpapi_api_key = Config.SERPAPI_API_KEY
        self.google_api_key = Config.GOOGLE_SEARCH_API_KEY
        self.google_engine_id = Config.GOOGLE_SEARCH_ENGINE_ID
        self.perplexity_key = Config.PERPLEXITY_API_KEY
        self.http_client = None
        self.wiki = None
        self.cost_tracker = cost_tracker
        self._serpapi_limiter = None
        self._perplexity_limiter = None

    @property
    def serpapi_limiter(self):
        if self._serpapi_limiter is None:
            self._serpapi_limiter = aiolimiter.AsyncLimiter(Config.SERPAPI_RPM, 60)
        return self._serpapi_limiter

    @property
    def perplexity_limiter(self):
        if self._perplexity_limiter is None:
            self._perplexity_limiter = aiolimiter.AsyncLimiter(Config.PERPLEXITY_RPM, 60)
        return self._perplexity_limiter

    async def __aenter__(self):
        self.http_client = httpx.AsyncClient(
            timeout=Config.TIMEOUT_SECONDS,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
            http2=True
        )
        self.wiki = AsyncWikipediaSearch(self.http_client)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.http_client:
            await self.http_client.aclose()

    @retry(stop=stop_after_attempt(Config.MAX_RETRIES), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def serpapi_search(self, query: str, num_results: int = 5, user_id: str = "default") -> ToolResult:
        if not self.serpapi_api_key:
            return ToolResult(success=False, error="SerpAPI key not configured", source="serpapi")

        if self.cost_tracker and not await self.cost_tracker.check_budget(user_id, "serpapi"):
            return ToolResult(success=False, error="Daily budget limit exceeded", source="serpapi")

        async with self.serpapi_limiter:
            try:
                url = "https://serpapi.com/search"
                params = {
                    "q": query,
                    "api_key": self.serpapi_api_key,
                    "num": num_results,
                    "engine": "google"
                }

                response = await self.http_client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                results = []
                citations = []

                for result in data.get("organic_results", [])[:num_results]:
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("link", ""),
                        "snippet": result.get("snippet", ""),
                        "position": result.get("position", 0)
                    })
                    if result.get("link"):
                        citations.append(result["link"])

                if "knowledge_graph" in data:
                    kg = data["knowledge_graph"]
                    kg_url = kg.get("source", {}).get("link", "")
                    results.insert(0, {
                        "title": kg.get("title", ""),
                        "url": kg_url,
                        "snippet": kg.get("description", ""),
                        "type": "knowledge_graph"
                    })
                    if kg_url:
                        citations.insert(0, kg_url)

                if self.cost_tracker:
                    await self.cost_tracker.record_cost(user_id, "serpapi")

                return ToolResult(
                    success=True,
                    data={"results": results, "query": query},
                    citations=citations,
                    source="serpapi",
                    cost=CostTracker.COSTS["serpapi"]
                )

            except Exception as e:
                return ToolResult(success=False, error=f"SerpAPI search failed: {str(e)}", source="serpapi")

    @retry(stop=stop_after_attempt(Config.MAX_RETRIES), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def google_search(self, query: str, num_results: int = 5, user_id: str = "default") -> ToolResult:
        if not self.google_api_key or not self.google_engine_id:
            return ToolResult(success=False, error="Google Search API not configured", source="google")

        if self.cost_tracker and not await self.cost_tracker.check_budget(user_id, "google-search"):
            return ToolResult(success=False, error="Daily budget limit exceeded", source="google")

        async with self.serpapi_limiter:
            try:
                url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    "key": self.google_api_key,
                    "cx": self.google_engine_id,
                    "q": query,
                    "num": num_results,
                }
                response = await self.http_client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                results = []
                citations = []
                for item in data.get("items", [])[:num_results]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                    })
                    if item.get("link"):
                        citations.append(item["link"])

                if self.cost_tracker:
                    await self.cost_tracker.record_cost(user_id, "google-search")

                return ToolResult(
                    success=True,
                    data={"results": results, "query": query},
                    citations=citations,
                    source="google",
                    cost=CostTracker.COSTS["google-search"]
                )

            except Exception as e:
                return ToolResult(success=False, error=f"Google search failed: {str(e)}", source="google")

    @retry(stop=stop_after_attempt(Config.MAX_RETRIES), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def perplexity_search(self, query: str, user_id: str = "default") -> ToolResult:
        if not self.perplexity_key:
            return ToolResult(success=False, error="Perplexity API key not configured", source="perplexity")

        if self.cost_tracker and not await self.cost_tracker.check_budget(user_id, "perplexity"):
            return ToolResult(success=False, error="Daily budget limit exceeded", source="perplexity")

        async with self.perplexity_limiter:
            try:
                url = "https://api.perplexity.ai/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.perplexity_key}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": "llama-3.1-sonar-large-128k-online",
                    "messages": [
                        {"role": "system", "content": "Be precise and do a deep dive. Provide factual information."},
                        {"role": "user", "content": query}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 2048,
                    "top_p": 0.9,
                    "return_citations": False,
                    "search_recency_filter": "month",
                    "stream": False
                }

                response = await self.http_client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

                answer = data["choices"][0]["message"]["content"]
                citations = data.get("citations", [])

                results = {
                    "answer": answer,
                    "query": query,
                    "model": data.get("model", ""),
                    "usage": data.get("usage", {})
                }

                if self.cost_tracker:
                    await self.cost_tracker.record_cost(user_id, "perplexity")

                return ToolResult(
                    success=True,
                    data=results,
                    citations=citations,
                    source="perplexity",
                    cost=CostTracker.COSTS["perplexity"]
                )

            except Exception as e:
                return ToolResult(success=False, error=f"Perplexity search failed: {str(e)}", source="perplexity")

    async def wiki_fetch(self, query: str, limit: int = 3, user_id: str = "default") -> ToolResult:
        """Async Wikipedia fetch (Fix #3)"""
        try:
            titles = await self.wiki.search(query, limit)
            if not titles:
                return ToolResult(success=False, error="No Wikipedia results found", source="wikipedia")

            tasks = [self.wiki.get_page_summary(title) for title in titles]
            pages = await asyncio.gather(*tasks, return_exceptions=True)
            valid_pages = [p for p in pages if isinstance(p, dict) and p is not None]

            citations = [p["url"] for p in valid_pages]
            return ToolResult(
                success=True,
                data={"pages": valid_pages, "query": query},
                citations=citations,
                source="wikipedia",
                cost=0.0
            )

        except Exception as e:
            return ToolResult(success=False, error=f"Wikipedia fetch failed: {str(e)}", source="wikipedia")


# ============================================================================
# VECTOR MEMORY SYSTEM
# ============================================================================

class VectorMemory:
    def __init__(self, embedding_service: EmbeddingService, api_key: str = None):
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
        try:
            existing_indexes = self.pc.list_indexes().names()
            if self.index_name not in existing_indexes:
                self.pc.create_index(
                    name=self.index_name,
                    dimension=Config.PINECONE_DIMENSION,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1")
                )
        except Exception as e:
            logger.warning("pinecone_index_setup_failed", error=str(e))

    async def query(self, text: str, namespace: str, top_k: int = 5,
                   filter_dict: Dict = None, user_id: str = "default") -> ToolResult:
        if not self.index:
            return ToolResult(success=False, error="Pinecone not configured")

        try:
            embedding = await self.embedding_service.embed(text, user_id)

            query_params = {
                "vector": embedding,
                "top_k": top_k,
                "namespace": namespace,
                "include_metadata": True
            }

            if filter_dict:
                query_params["filter"] = filter_dict

            results = self.index.query(**query_params)

            matches = []
            for match in results.get("matches", []):
                score = match.get("score", 0.0)
                # Use configurable threshold (Fix #1)
                if score >= Config.MEMORY_SIMILARITY_THRESHOLD:
                    matches.append({
                        "id": match.get("id", ""),
                        "score": score,
                        "text": match.get("metadata", {}).get("text", ""),
                        "metadata": match.get("metadata", {}),
                        "timestamp": match.get("metadata", {}).get("timestamp", "")
                    })

            return ToolResult(success=True, data={"matches": matches, "namespace": namespace})

        except Exception as e:
            logger.error("memory_query_failed", error=str(e), user_id=user_id)
            return ToolResult(success=False, error=f"Memory query failed: {str(e)}")

    async def upsert(self, items: List[Dict], namespace: str, user_id: str = "default") -> ToolResult:
        if not self.index:
            return ToolResult(success=False, error="Pinecone not configured")

        try:
            vectors = []
            texts = [item["text"] for item in items]
            embeddings = await self.embedding_service.embed_batch(texts, user_id)
            timestamp = datetime.now(timezone.utc).isoformat()

            for item, embedding in zip(items, embeddings):
                vector_id = hashlib.md5(f"{item['text']}{timestamp}".encode()).hexdigest()
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

            self.index.upsert(vectors=vectors, namespace=namespace)
            return ToolResult(success=True, data={"stored": len(vectors), "namespace": namespace})

        except Exception as e:
            logger.error("memory_upsert_failed", error=str(e), user_id=user_id)
            return ToolResult(success=False, error=f"Memory upsert failed: {str(e)}")


# ============================================================================
# PROFILE MANAGER & UNIFIED MEMORY (Fix #6)
# ============================================================================

class ProfileManager:
    def __init__(self, storage_dir: str = None):
        self.storage_dir = storage_dir or Config.PROFILE_DIR
        os.makedirs(self.storage_dir, exist_ok=True)
        self.cache: Dict[str, Dict] = {}

    def _profile_path(self, user_id: str) -> str:
        safe_id = hashlib.md5(user_id.encode()).hexdigest()
        return os.path.join(self.storage_dir, f"{safe_id}.json")

    async def read(self, user_id: str, keys: List[str] = None) -> Dict:
        if user_id in self.cache:
            profile = self.cache[user_id]
        else:
            path = self._profile_path(user_id)
            if os.path.exists(path):
                try:
                    async with aiofiles.open(path, 'r') as f:
                        content = await f.read()
                        profile = json.loads(content)
                        self.cache[user_id] = profile
                except Exception as e:
                    logger.error("profile_read_failed", user_id=user_id, error=str(e))
                    profile = {}
            else:
                profile = {}

        if keys:
            return {k: profile.get(k) for k in keys if k in profile}
        return profile

    async def write(self, user_id: str, data: Dict) -> bool:
        try:
            profile = await self.read(user_id)
            profile.update(data)
            self.cache[user_id] = profile

            path = self._profile_path(user_id)
            async with aiofiles.open(path, 'w') as f:
                await f.write(json.dumps(profile, indent=2))
            return True
        except Exception as e:
            logger.error("profile_write_failed", user_id=user_id, error=str(e))
            return False


class UnifiedMemorySystem:
    """Integrated profile and vector memory (Fix #6)"""

    def __init__(self, vector_memory: VectorMemory, profile_manager: ProfileManager):
        self.vector_memory = vector_memory
        self.profile_manager = profile_manager

    async def get_context(self, user_id: str, query: str) -> Dict[str, Any]:
        profile = await self.profile_manager.read(user_id)
        namespace = f"user:{user_id}"
        memory_result = await self.vector_memory.query(query, namespace, top_k=5, user_id=user_id)

        memories = []
        if memory_result.success:
            memories = memory_result.data.get("matches", [])

        return {
            "profile": profile,
            "memories": memories,
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# TOOL EXECUTOR (Fix #10)
# ============================================================================

class ToolExecutor:
    """Enhanced tool executor with validation"""

    TOOL_SCHEMAS = {
        "web_search": {"required": ["query"], "optional": {"num": int}},
        "google_search": {"required": ["query"], "optional": {"num": int}},
        "perplexity_search": {"required": ["query"], "optional": {}},
        "wiki_fetch": {"required": ["query"], "optional": {"limit": int}},
        "memory_query": {"required": ["text"], "optional": {"top_k": int, "filter": dict}},
        "memory_upsert": {"required": ["items"], "optional": {}},
        "profile_read": {"required": ["keys"], "optional": {}},
        "profile_write": {"required": ["data"], "optional": {}}
    }

    def __init__(self, cost_tracker: CostTracker = None):
        self.cost_tracker = cost_tracker
        self.embedding_service = EmbeddingService(cost_tracker=cost_tracker)
        self.vector_memory = VectorMemory(self.embedding_service)
        self.profile_manager = ProfileManager()
        self.unified_memory = UnifiedMemorySystem(self.vector_memory, self.profile_manager)
        self.search_engine = None

    async def __aenter__(self):
        self.search_engine = await SearchEngine(cost_tracker=self.cost_tracker).__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.search_engine:
            await self.search_engine.__aexit__(exc_type, exc_val, exc_tb)

    def validate_tool_call(self, tool_name: str, arguments: Dict) -> Tuple[bool, Optional[str]]:
        """Enhanced validation with schemas (Fix #10)"""
        try:
            if tool_name not in self.TOOL_SCHEMAS:
                return False, f"Unknown tool: {tool_name}"

            schema = self.TOOL_SCHEMAS[tool_name]

            for param in schema["required"]:
                if param not in arguments:
                    return False, f"Missing required parameter: {param}"

                if param == "items" and not isinstance(arguments[param], list):
                    return False, f"Parameter 'items' must be a list"
                if param == "keys" and not isinstance(arguments[param], list):
                    return False, f"Parameter 'keys' must be a list"
                if param == "data" and not isinstance(arguments[param], dict):
                    return False, f"Parameter 'data' must be a dict"

            for param, expected_type in schema["optional"].items():
                if param in arguments and not isinstance(arguments[param], expected_type):
                    return False, f"Parameter '{param}' must be of type {expected_type.__name__}"

            return True, None

        except Exception as e:
            return False, str(e)

    async def execute(self, tool_name: str, arguments: Dict, user_id: str = "default") -> ToolResult:
        is_valid, error = self.validate_tool_call(tool_name, arguments)
        if not is_valid:
            return ToolResult(success=False, error=error)

        try:
            if tool_name == ToolType.WEB_SEARCH.value:
                return await self.search_engine.serpapi_search(
                    arguments.get("query", ""), arguments.get("num", 5), user_id)

            elif tool_name == ToolType.PERPLEXITY_SEARCH.value:
                return await self.search_engine.perplexity_search(
                    arguments.get("query", ""), user_id)

            elif tool_name == ToolType.GOOGLE_SEARCH.value:
                return await self.search_engine.google_search(
                    arguments.get("query", ""), arguments.get("num", 5), user_id)

            elif tool_name == ToolType.WIKI_FETCH.value:
                return await self.search_engine.wiki_fetch(
                    arguments.get("query", ""), arguments.get("limit", 3), user_id)

            elif tool_name == ToolType.MEMORY_QUERY.value:
                namespace = f"user:{user_id}"
                return await self.vector_memory.query(
                    arguments.get("text", ""), namespace,
                    arguments.get("top_k", 5), arguments.get("filter"), user_id)

            elif tool_name == ToolType.MEMORY_UPSERT.value:
                namespace = f"user:{user_id}"
                return await self.vector_memory.upsert(
                    arguments.get("items", []), namespace, user_id)

            elif tool_name == ToolType.PROFILE_READ.value:
                data = await self.profile_manager.read(user_id, arguments.get("keys"))
                return ToolResult(success=True, data=data)

            elif tool_name == ToolType.PROFILE_WRITE.value:
                success = await self.profile_manager.write(user_id, arguments.get("data", {}))
                return ToolResult(success=success, data={"updated": list(arguments.get("data", {}).keys())})

            else:
                return ToolResult(success=False, error=f"Tool not implemented: {tool_name}")

        except Exception as e:
            logger.error("tool_execution_failed", tool=tool_name, error=str(e))
            return ToolResult(success=False, error=f"Tool execution failed: {str(e)}")


# ============================================================================
# MAIN AGENT (Fix #1, #2, #4)
# ============================================================================

class AutonomousAgent:
    """Enhanced agent with improved memory and conversation management"""

    def __init__(self, openai_api_key: str = None, cost_tracker: CostTracker = None):
        self.openai_api_key = openai_api_key or Config.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=self.openai_api_key) if self.openai_api_key else None
        self.cost_tracker = cost_tracker or CostTracker()
        self.tool_executor = None
        self.conversation_history: List[Dict] = []
        self.citation_manager = CitationManager()
        self.max_iterations = 10
        self._rate_limiter = None

    @property
    def rate_limiter(self):
        if self._rate_limiter is None:
            self._rate_limiter = aiolimiter.AsyncLimiter(Config.OPENAI_RPM, 60)
        return self._rate_limiter

    async def __aenter__(self):
        self.tool_executor = await ToolExecutor(cost_tracker=self.cost_tracker).__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.tool_executor:
            await self.tool_executor.__aexit__(exc_type, exc_val, exc_tb)

    def _get_function_definitions(self) -> List[Dict]:
        """Tool definitions with cost guidance (Fix #2)"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": """Search web using SerpAPI. COST: Low ($0.002). USE FOR: Current events, news, simple facts. TIP: Default choice for most queries.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "num": {"type": "integer", "description": "Results (default 5)", "default": 5}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "google_search",
                    "description": """Google Custom Search. COST: Medium ($0.005). USE: Fallback when SerpAPI unavailable.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "num": {"type": "integer", "default": 5}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "perplexity_search",
                    "description": """Perplexity AI. COST: High. USE ONLY FOR: Complex analysis, synthesis, multi-source integration.""",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "wiki_fetch",
                    "description": """Wikipedia. COST: Free. USE FIRST for: Encyclopedic knowledge, definitions, facts.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "limit": {"type": "integer", "default": 3}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "memory_query",
                    "description": """Search user memories. USE WHEN: User references past, preferences, prior context.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "top_k": {"type": "integer", "default": 5}
                        },
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "memory_upsert",
                    "description": """Store user info. STORE: Preferences, personal facts, context.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "text": {"type": "string"},
                                        "meta": {"type": "object"}
                                    },
                                    "required": ["text"]
                                }
                            }
                        },
                        "required": ["items"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "profile_read",
                    "description": "Read user profile",
                    "parameters": {
                        "type": "object",
                        "properties": {"keys": {"type": "array", "items": {"type": "string"}}},
                        "required": ["keys"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "profile_write",
                    "description": "Update user profile",
                    "parameters": {
                        "type": "object",
                        "properties": {"data": {"type": "object"}},
                        "required": ["data"]
                    }
                }
            }
        ]

    def _estimate_tokens(self, messages: List[Dict]) -> int:
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += len(content) // 4
        return total

    async def _summarize_conversation(self, messages: List[Dict], user_id: str) -> str:
        """Summarize conversation (Fix #4)"""
        try:
            if not await self.cost_tracker.check_budget(user_id, "gpt-4o-mini-input", 1000):
                return "Previous context"

            conversation_text = "\n".join([
                f"{msg.get('role')}: {msg.get('content', '')[:200]}"
                for msg in messages if msg.get('content')
            ])

            response = await self.client.chat.completions.create(
                model=Config.SUMMARY_MODEL,
                messages=[{
                    "role": "user",
                    "content": f"Summarize concisely in 2-3 sentences:\n{conversation_text}"
                }],
                max_tokens=300,
                temperature=0.3,
            )

            summary = response.choices[0].message.content
            usage = response.usage
            await self.cost_tracker.record_cost(user_id, "gpt-4o-mini-input", usage.prompt_tokens)
            await self.cost_tracker.record_cost(user_id, "gpt-4o-mini-output", usage.completion_tokens)
            return summary

        except Exception:
            return "Previous context"

    async def _manage_conversation_history(self, user_id: str):
        """Smart history with summarization (Fix #4)"""
        token_count = self._estimate_tokens(self.conversation_history)

        if token_count > 8000:
            system_msgs = [msg for msg in self.conversation_history if msg["role"] == "system"]
            recent = self.conversation_history[-10:]
            to_summarize = self.conversation_history[len(system_msgs):-10]

            if to_summarize:
                summary = await self._summarize_conversation(to_summarize, user_id)
                self.conversation_history = [
                    *system_msgs,
                    {"role": "system", "content": f"[Previous summary]: {summary}"},
                    *recent
                ]

    async def _extract_memories(self, conversation: List[Dict], user_id: str):
        """Auto-extract memories (Fix #1)"""
        if not Config.AUTO_MEMORY_EXTRACTION:
            return

        try:
            if not await self.cost_tracker.check_budget(user_id, "gpt-4o-mini-input", 2000):
                return

            user_messages = [
                msg.get("content", "") for msg in conversation[-5:]
                if msg.get("role") == "user" and msg.get("content")
            ]

            if not user_messages:
                return

            conversation_text = "\n".join(user_messages)

            response = await self.client.chat.completions.create(
                model=Config.SUMMARY_MODEL,
                messages=[{
                    "role": "user",
                    "content": f"""Extract important facts about the user from this conversation. Return JSON array or empty []:
{conversation_text}

[{{"text": "fact", "meta": {{"category": "preference|personal|goal"}}}}]"""
                }],
                max_tokens=300,
                temperature=0.2
            )

            result = response.choices[0].message.content.strip()
            usage = response.usage
            await self.cost_tracker.record_cost(user_id, "gpt-4o-mini-input", usage.prompt_tokens)
            await self.cost_tracker.record_cost(user_id, "gpt-4o-mini-output", usage.completion_tokens)

            try:
                memories = json.loads(result)
                if memories and isinstance(memories, list):
                    await self.tool_executor.execute("memory_upsert", {"items": memories}, user_id)
            except json.JSONDecodeError:
                pass

        except Exception:
            pass

    async def chat(self, user_message: str, user_id: str = "default") -> str:
        """Main chat with enhanced features"""
        if not self.client:
            return "❌ OpenAI API not configured"

        if not await self.cost_tracker.check_budget(user_id, "gpt-4o-input", 1000):
            costs = await self.cost_tracker.get_user_costs(user_id)
            return f"❌ Budget limit reached. ${costs['total']:.3f} / ${costs['limit']:.2f}"

        self.citation_manager.clear()

        system_message = {
            "role": "system",
            "content": """Autonomous assistant with tools.

TOOL COST STRATEGY:
1. wiki_fetch: FREE - Try first for encyclopedic topics
2. web_search: CHEAP - Default for most queries
3. google_search: MEDIUM - Use if web_search fails
4. perplexity_search: EXPENSIVE - Only for complex analysis

Always cite sources [1], [2]. Store important user info automatically."""
        }

        if not self.conversation_history or self.conversation_history[0]["role"] != "system":
            self.conversation_history = [system_message]

        self.conversation_history.append({"role": "user", "content": user_message})

        iterations = 0

        while iterations < self.max_iterations:
            iterations += 1
            await self._manage_conversation_history(user_id)

            async with self.rate_limiter:
                try:
                    response = await self.client.chat.completions.create(
                        model=Config.CHAT_MODEL,
                        messages=self.conversation_history,
                        tools=self._get_function_definitions(),
                        tool_choice="auto",
                        temperature=0.3,
                        max_tokens=8000
                    )

                    usage = response.usage
                    await self.cost_tracker.record_cost(user_id, "gpt-4o-input", usage.prompt_tokens)
                    await self.cost_tracker.record_cost(user_id, "gpt-4o-output", usage.completion_tokens)

                    assistant_message = response.choices[0].message

                    if assistant_message.tool_calls:
                        self.conversation_history.append({
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

                        for tool_call in assistant_message.tool_calls:
                            function_name = tool_call.function.name
                            try:
                                function_args = json.loads(tool_call.function.arguments)
                            except json.JSONDecodeError:
                                function_args = {}

                            result = await self.tool_executor.execute(function_name, function_args, user_id)

                            if result.citations:
                                self.citation_manager.add_citations(result.citations)

                            if result.success:
                                data_str = json.dumps(result.data, indent=2)
                                if len(data_str) > 2000:
                                    data_str = data_str[:2000] + "\n... (truncated)"
                                tool_response = f"Success from {result.source or function_name}:\n{data_str}"
                            else:
                                tool_response = f"Error: {result.error}"

                            self.conversation_history.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": function_name,
                                "content": tool_response
                            })

                        continue

                    else:
                        final_answer = assistant_message.content or "I couldn't generate a response."
                        final_answer += self.citation_manager.format_citations()

                        if Config.ENABLE_COST_TRACKING:
                            costs = await self.cost_tracker.get_user_costs(user_id)
                            final_answer += f"\n\n💰 Usage: ${costs['total']:.4f} / ${costs['limit']:.2f}"

                        self.conversation_history.append({
                            "role": "assistant",
                            "content": final_answer
                        })

                        await self._extract_memories(self.conversation_history[-6:], user_id)
                        return final_answer

                except Exception as e:
                    logger.error("chat_failed", error=str(e))
                    return f"❌ Error: {str(e)}"

        return "⚠️ Max iterations reached. Try rephrasing."

    def clear_history(self):
        self.conversation_history.clear()


# ============================================================================
# MAIN INTERFACE
# ============================================================================

class AutonomousAssistant:
    """Main assistant interface"""

    def __init__(self, cost_tracker: CostTracker = None):
        self.cost_tracker = cost_tracker or CostTracker()
        self.agent = None

    async def __aenter__(self):
        self.agent = await AutonomousAgent(cost_tracker=self.cost_tracker).__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.agent:
            await self.agent.__aexit__(exc_type, exc_val, exc_tb)

    async def chat(self, message: str, user_id: str = "default") -> str:
        return await self.agent.chat(message, user_id)

    def clear_history(self):
        if self.agent:
            self.agent.clear_history()

    async def get_costs(self, user_id: str = "default") -> Dict[str, float]:
        return await self.cost_tracker.get_user_costs(user_id)


# ============================================================================
# CLI
# ============================================================================

async def main():
    print("🧠 Autonomous Assistant v3.0 (Enhanced)")
    print("=" * 70)
    print("✅ Fixes: #1,#2,#3,#4,#6,#7,#8,#9,#10")
    print("=" * 70)
    print("\nCommands: exit | clear | config | costs\n")

    user_id = "cli_user"

    async with AutonomousAssistant() as assistant:
        try:
            while True:
                try:
                    user_input = input("\n🧑 You: ").strip()

                    if not user_input:
                        continue

                    if user_input.lower() == 'exit':
                        costs = await assistant.get_costs(user_id)
                        print(f"\n💰 Final: ${costs['total']:.4f}")
                        print("👋 Goodbye!")
                        break

                    if user_input.lower() == 'clear':
                        assistant.clear_history()
                        print("✅ History cleared")
                        continue

                    if user_input.lower() == 'costs':
                        costs = await assistant.get_costs(user_id)
                        print(f"\n💰 Today: ${costs['total']:.4f} / ${costs['limit']:.2f}")
                        continue

                    if user_input.lower() == 'config':
                        print("\n📋 Status:")
                        print(f"  OpenAI: {'✅' if Config.OPENAI_API_KEY else '❌'}")
                        print(f"  Pinecone: {'✅' if Config.PINECONE_API_KEY else '❌'}")
                        print(f"  SerpAPI: {'✅' if Config.SERPAPI_API_KEY else '❌'}")
                        print(f"  Google: {'✅' if Config.GOOGLE_SEARCH_API_KEY else '❌'}")
                        print(f"  Perplexity: {'✅' if Config.PERPLEXITY_API_KEY else '❌'}")
                        continue

                    print("\n🤔 Processing...\n")
                    response = await assistant.chat(user_input, user_id)
                    print(f"🤖 Assistant:\n\n{response}")

                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")

        except Exception as e:
            print(f"Fatal: {e}")


if __name__ == "__main__":
    asyncio.run(main())