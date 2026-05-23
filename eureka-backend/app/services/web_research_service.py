"""
WebResearchService - Fetches real-world information about objects from Wikipedia.

Used by ObjectArchitectAgent to inject factual data (materials, colors, dimensions,
structure) into LLM prompts so generated 3D assemblies are physically accurate.
"""

import logging
import urllib.parse
from typing import Dict, Any

import httpx

logger = logging.getLogger(__name__)

WIKIPEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
WIKIPEDIA_SEARCH_URL = "https://en.wikipedia.org/w/api.php"


class WebResearchService:
    """Fetches factual information about objects from Wikipedia REST API."""

    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout

    async def research_object(self, query: str) -> Dict[str, Any]:
        """
        Research an object by querying Wikipedia for real-world information.

        Args:
            query: The object name/description to research (e.g. "car engine", "telescope").

        Returns:
            A dict with keys: title, description, image_url, details.
            Returns empty dict on any failure.
        """
        if not query or not query.strip():
            return {}

        try:
            # First, try a direct page summary lookup
            result = await self._fetch_page_summary(query.strip())
            if result:
                return result

            # If direct lookup failed, search Wikipedia and try the top result
            search_title = await self._search_wikipedia(query.strip())
            if search_title:
                result = await self._fetch_page_summary(search_title)
                if result:
                    return result

            logger.info(f"No Wikipedia data found for query: '{query}'")
            return {}

        except Exception as e:
            logger.warning(f"WebResearchService error for '{query}': {e}")
            return {}

    async def _fetch_page_summary(self, title: str) -> Dict[str, Any] | None:
        """
        Fetch the summary of a Wikipedia page by title.

        Returns a dict with title, description, image_url, details or None on failure.
        """
        encoded_title = urllib.parse.quote(title.replace(" ", "_"), safe="")
        url = WIKIPEDIA_SUMMARY_URL.format(title=encoded_title)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers={
                    "User-Agent": "EUREKA-3D-Backend/1.0 (research; educational)",
                    "Accept": "application/json",
                })

            if response.status_code == 404:
                return None

            if response.status_code != 200:
                logger.warning(f"Wikipedia summary API returned {response.status_code} for '{title}'")
                return None

            data = response.json()

            # Skip disambiguation pages
            if data.get("type") == "disambiguation":
                return None

            result = {
                "title": data.get("title", title),
                "description": data.get("description", ""),
                "image_url": "",
                "details": data.get("extract", ""),
            }

            # Extract thumbnail URL if available
            thumbnail = data.get("thumbnail")
            if thumbnail and isinstance(thumbnail, dict):
                result["image_url"] = thumbnail.get("source", "")

            return result

        except httpx.TimeoutException:
            logger.warning(f"Wikipedia summary request timed out for '{title}'")
            return None
        except Exception as e:
            logger.warning(f"Failed to fetch Wikipedia summary for '{title}': {e}")
            return None

    async def _search_wikipedia(self, query: str) -> str | None:
        """
        Search Wikipedia for a query string and return the title of the best match.

        Returns the title string of the top result, or None if no results.
        """
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": "3",
            "format": "json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(WIKIPEDIA_SEARCH_URL, params=params, headers={
                    "User-Agent": "EUREKA-3D-Backend/1.0 (research; educational)",
                    "Accept": "application/json",
                })

            if response.status_code != 200:
                logger.warning(f"Wikipedia search API returned {response.status_code} for '{query}'")
                return None

            data = response.json()
            search_results = data.get("query", {}).get("search", [])

            if not search_results:
                return None

            # Return the title of the best match
            return search_results[0].get("title")

        except httpx.TimeoutException:
            logger.warning(f"Wikipedia search request timed out for '{query}'")
            return None
        except Exception as e:
            logger.warning(f"Failed to search Wikipedia for '{query}': {e}")
            return None
