"""
Search services package
UPDATED: Added Kagi FastGPT search integration
"""

from src.services.search.base import BaseSearchEngine
from src.services.search.wikipedia import WikipediaSearch
from src.services.search.serpapi import SerpAPISearch
from src.services.search.google import GoogleSearch
from src.services.search.perplexity import PerplexitySearch
from src.services.search.kagi_search import KagiSearch  # NEW

__all__ = [
    "BaseSearchEngine",
    "WikipediaSearch",
    "SerpAPISearch",
    "GoogleSearch",
    "PerplexitySearch",
    "KagiSearch",  # NEW
]