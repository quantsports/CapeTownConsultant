"""
Wikipedia search implementation
"""

import asyncio
import time
from typing import List, Optional, Dict

from src.services.search.base import BaseSearchEngine
from src.core.models import ToolResult
from src.core.metrics import get_metrics


class WikipediaSearch(BaseSearchEngine):
    """Async Wikipedia search"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = "https://en.wikipedia.org/w/api.php"

    async def search_titles(self, query: str, limit: int = 3) -> List[str]:
        """Search for article titles"""
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
        """Get page summary"""
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

    async def search(
        self,
        query: str,
        user_id: str = "default",
        limit: int = 3
    ) -> ToolResult:
        """Search Wikipedia and return results"""
        metrics = get_metrics()
        metrics.record_tool_usage("wikipedia")
        _t0 = time.perf_counter()
        try:
            titles = await self.search_titles(query, limit)
            if not titles:
                metrics.record_response_time("wikipedia", (time.perf_counter() - _t0) * 1000.0)
                return ToolResult(
                    success=False,
                    error="wikipedia failed: NotFoundError - No results found",
                    source="wikipedia"
                )

            # Fetch summaries for all titles
            tasks = [self.get_page_summary(title) for title in titles]
            pages = await asyncio.gather(*tasks, return_exceptions=True)
            valid_pages = [p for p in pages if isinstance(p, dict) and p is not None]

            citations = [p["url"] for p in valid_pages]

            metrics.record_response_time("wikipedia", (time.perf_counter() - _t0) * 1000.0)
            return ToolResult(
                success=True,
                data={"pages": valid_pages, "query": query},
                citations=citations,
                source="wikipedia",
                cost=0.0  # Wikipedia is free
            )

        except Exception as e:
            metrics.record_response_time("wikipedia", (time.perf_counter() - _t0) * 1000.0)
            return ToolResult(
                success=False,
                error=f"wikipedia failed: {e.__class__.__name__} - {str(e)}",
                source="wikipedia"
            )