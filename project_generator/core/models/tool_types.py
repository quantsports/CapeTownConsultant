from enum import Enum

class ToolType(str, Enum):
    """Available tool types"""
    WEB_SEARCH = "web_search"
    WIKI_FETCH = "wiki_fetch"
    MEMORY_QUERY = "memory_query"
    PERPLEXITY_SEARCH = "perplexity_search"
    GOOGLE_SEARCH = "google_search"
