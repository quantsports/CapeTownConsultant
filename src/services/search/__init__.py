"""
Search services package
Unified interface for all search engines
"""

from src.services.search.wikipedia import WikipediaSearch
from src.services.search.serpapi import SerpAPISearch
from src.services.search.google import GoogleSearch
from src.services.search.perplexity import PerplexitySearch

__all__ = [
    "WikipediaSearch",
    "SerpAPISearch",
    "GoogleSearch",
    "PerplexitySearch"
]