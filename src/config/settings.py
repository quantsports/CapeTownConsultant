"""
Configuration management for the assistant
Centralized settings and environment variable handling
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# Load environment variables at module import
load_dotenv(find_dotenv())


class Config:
    """Centralized configuration for the assistant"""

    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
    GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY")
    GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

    # Pinecone Configuration
    PINECONE_INDEX = os.getenv("PINECONE_INDEX", "assistant-memory")
    PINECONE_DIMENSION = 1536

    # Model Configuration
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o")
    SUMMARY_MODEL = os.getenv("SUMMARY_MODEL", "gpt-4o-mini")

    # API Settings
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))
    TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "30"))
    MAX_CONVERSATION_HISTORY = int(os.getenv("MAX_CONVERSATION_HISTORY", "20"))
    CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "1000"))
    MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "10"))

    # Rate Limiting (requests per minute)
    OPENAI_RPM = int(os.getenv("OPENAI_RPM", "50"))
    SERPAPI_RPM = int(os.getenv("SERPAPI_RPM", "100"))
    PERPLEXITY_RPM = int(os.getenv("PERPLEXITY_RPM", "20"))

    # Memory Settings
    MEMORY_SIMILARITY_THRESHOLD = float(os.getenv("MEMORY_SIMILARITY_THRESHOLD", "0.65"))
    AUTO_MEMORY_EXTRACTION = os.getenv("AUTO_MEMORY_EXTRACTION", "True").lower() == "true"

    # Cost Tracking
    ENABLE_COST_TRACKING = os.getenv("ENABLE_COST_TRACKING", "True").lower() == "true"
    DAILY_BUDGET_LIMIT = float(os.getenv("DAILY_BUDGET_LIMIT", "5.0"))

    # Directory Paths
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = BASE_DIR / "data"
    PROFILE_DIR = DATA_DIR / "profiles"
    CONVERSATION_DIR = DATA_DIR / "conversations"
    CACHE_DIR = BASE_DIR / "cache"
    EMBEDDING_CACHE_DIR = CACHE_DIR / "embeddings"
    LOG_DIR = CACHE_DIR / "logs"

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # Metrics
    METRICS_ENABLED = os.getenv("METRICS_ENABLED", "True").lower() == "true"

    @classmethod
    def ensure_directories(cls):
        """Create required directories if they don't exist"""
        directories = [
            cls.DATA_DIR,
            cls.PROFILE_DIR,
            cls.CONVERSATION_DIR,
            cls.CACHE_DIR,
            cls.EMBEDDING_CACHE_DIR,
            cls.LOG_DIR,
        ]

        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"Warning: Could not create directory {directory}: {e}", file=sys.stderr)

    @classmethod
    def validate_required_keys(cls) -> dict:
        """Check which API keys are configured"""
        return {
            "openai": bool(cls.OPENAI_API_KEY),
            "pinecone": bool(cls.PINECONE_API_KEY),
            "serpapi": bool(cls.SERPAPI_API_KEY),
            "google_search": bool(cls.GOOGLE_SEARCH_API_KEY and cls.GOOGLE_SEARCH_ENGINE_ID),
            "perplexity": bool(cls.PERPLEXITY_API_KEY),
        }

    @classmethod
    def validate_critical_keys(cls, warn: bool = True) -> bool:
        """
        Validate that critical API keys are present

        Args:
            warn: If True, print warnings for missing keys

        Returns:
            True if OpenAI key is present (minimum requirement)
        """
        keys_status = cls.validate_required_keys()

        if not keys_status["openai"]:
            if warn:
                print("ERROR: OPENAI_API_KEY is required but not configured", file=sys.stderr)
            return False

        if warn:
            missing = [name for name, present in keys_status.items() if not present and name != "openai"]
            if missing:
                print(f"Warning: Optional API keys not configured: {', '.join(missing)}", file=sys.stderr)

        return True

    @classmethod
    def get_config_summary(cls) -> dict:
        """Get a summary of current configuration"""
        return {
            "api_keys": cls.validate_required_keys(),
            "models": {
                "chat": cls.CHAT_MODEL,
                "embedding": cls.EMBEDDING_MODEL,
                "summary": cls.SUMMARY_MODEL,
            },
            "limits": {
                "max_retries": cls.MAX_RETRIES,
                "timeout": cls.TIMEOUT_SECONDS,
                "daily_budget": cls.DAILY_BUDGET_LIMIT,
            },
            "paths": {
                "data": str(cls.DATA_DIR),
                "cache": str(cls.CACHE_DIR),
            }
        }


# Initialize directories on import
try:
    Config.ensure_directories()
except Exception as e:
    print(f"Warning: Initialization error: {e}", file=sys.stderr)

# Validate critical configuration
if not Config.validate_critical_keys(warn=False):
    print("\n⚠️  Configuration Warning: OPENAI_API_KEY not found in environment", file=sys.stderr)
    print("Please set it in your .env file or environment variables\n", file=sys.stderr)



