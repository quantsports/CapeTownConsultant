"""
Configuration settings
Centralized configuration management
UPDATED: Added Kagi FastGPT API configuration
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration constants and environment variables"""

    # =========================================================================
    # API Keys
    # =========================================================================
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
    GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY")
    GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

    # NEW: Kagi FastGPT API
    KAGI_API_KEY = os.getenv("KAGI_API_KEY")

    # =========================================================================
    # Models
    # =========================================================================
    CHAT_MODEL = "gpt-4o"
    SUMMARY_MODEL = "gpt-4o-mini"
    EMBEDDING_MODEL = "text-embedding-3-small"

    # =========================================================================
    # Pinecone
    # =========================================================================
    PINECONE_INDEX = "assistant-memory"
    PINECONE_DIMENSION = 1536
    PINECONE_REGION = "us-east-1"

    # =========================================================================
    # Rate Limits (requests per minute)
    # =========================================================================
    OPENAI_RPM = 50
    SERPAPI_RPM = 100
    PERPLEXITY_RPM = 20
    KAGI_RPM = 30  # NEW: Conservative rate limit for Kagi

    # =========================================================================
    # Costs (per 1000 tokens or per call)
    # =========================================================================
    # Note: These are also in CostTracker.COSTS for backward compatibility
    # NEW: Kagi added to cost tracking
    COST_GPT4O_INPUT = 0.0025
    COST_GPT4O_OUTPUT = 0.01
    COST_EMBEDDING = 0.00002
    COST_SERPAPI = 0.002
    COST_GOOGLE_SEARCH = 0.005
    COST_PERPLEXITY = 0.001
    COST_KAGI = 0.015  # NEW: $0.015 per query

    # =========================================================================
    # Thresholds
    # =========================================================================
    MEMORY_SIMILARITY_THRESHOLD = 0.7
    MAX_CONTEXT_TOKENS = 8000
    MAX_CONVERSATION_LENGTH = 20
    MAX_CONVERSATION_HISTORY = 20  # Maximum messages to keep in conversation history

    # =========================================================================
    # Features
    # =========================================================================
    AUTO_MEMORY_EXTRACTION = True
    ENABLE_COST_TRACKING = True
    ENABLE_CACHING = True

    # =========================================================================
    # Timeouts and Retries
    # =========================================================================
    TIMEOUT_SECONDS = 30.0
    MAX_RETRIES = 3

    # =========================================================================
    # Budget
    # =========================================================================
    DAILY_BUDGET_LIMIT = 59999.0  # USD

    # =========================================================================
    # Paths
    # =========================================================================
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = BASE_DIR / "data"
    CACHE_DIR = BASE_DIR / "cache"

    PROFILE_DIR = DATA_DIR / "profiles"
    CONVERSATION_DIR = DATA_DIR / "conversations"

    EMBEDDING_CACHE_DIR = CACHE_DIR / "embeddings"
    COST_DIR = CACHE_DIR / "costs"
    LOG_DIR = CACHE_DIR / "logs"

    # Create directories
    for directory in [
        PROFILE_DIR,
        CONVERSATION_DIR,
        EMBEDDING_CACHE_DIR,
        COST_DIR,
        LOG_DIR
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # Cache Settings
    # =========================================================================
    CACHE_MAX_SIZE = 1000
    CACHE_TTL = 3600  # 1 hour

    # =========================================================================
    # Logging
    # =========================================================================
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = LOG_DIR / "app.log"
    ERROR_LOG_FILE = LOG_DIR / "errors.log"

    # =========================================================================
    # Thresholds
    # =========================================================================
    MAX_ITERATIONS = 10  # Maximum iterations for autonomous agent tool execution loop

    @classmethod
    def is_configured(cls, service: str) -> bool:
        """
        Check if a service is configured

        Args:
            service: Service name (openai, pinecone, serpapi, google, perplexity, kagi)

        Returns:
            True if API key is configured
        """
        key_map = {
            "openai": cls.OPENAI_API_KEY,
            "pinecone": cls.PINECONE_API_KEY,
            "serpapi": cls.SERPAPI_API_KEY,
            "google": cls.GOOGLE_SEARCH_API_KEY and cls.GOOGLE_SEARCH_ENGINE_ID,
            "perplexity": cls.PERPLEXITY_API_KEY,
            "kagi": cls.KAGI_API_KEY,  # NEW
        }

        value = key_map.get(service.lower())
        return value is not None and value != ""

    @classmethod
    def get_configured_services(cls) -> dict:
        """
        Get configuration status of all services

        Returns:
            Dictionary mapping service names to configuration status
        """
        return {
            "openai": cls.is_configured("openai"),
            "pinecone": cls.is_configured("pinecone"),
            "serpapi": cls.is_configured("serpapi"),
            "google": cls.is_configured("google"),
            "perplexity": cls.is_configured("perplexity"),
            "kagi": cls.is_configured("kagi"),  # NEW
        }
