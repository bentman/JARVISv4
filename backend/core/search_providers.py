"""
Web search providers for JARVISv4.
Ported from JARVISv3 for deterministic external knowledge retrieval.
"""
import logging
import httpx
from typing import List, Dict, Optional, Any
from abc import ABC, abstractmethod
from ddgs import DDGS

logger = logging.getLogger(__name__)

class WebSearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Perform web search and return normalized results"""
        pass

class DuckDuckGoProvider(WebSearchProvider):
    def __init__(self):
        self.ddgs = DDGS()

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        try:
            import asyncio
            # duckduckgo_search is synchronous, wrap in thread for async safety
            web_hits = await asyncio.to_thread(self.ddgs.text, query, max_results=max_results)
            return [
                {
                    "title": r.get("title"),
                    "url": r.get("href"),
                    "snippet": r.get("body"),
                    "source": "duckduckgo"
                }
                for r in web_hits
            ]
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return []

class BingProvider(WebSearchProvider):
    def __init__(self, api_key: str, endpoint: str = "https://api.bing.microsoft.com/v7.0/search"):
        self.api_key = api_key
        self.endpoint = endpoint

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        params = {"q": query, "count": max_results}

        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(self.endpoint, headers=headers, params=params, timeout=10.0)
                r.raise_for_status()
                data = r.json()

            results = []
            for item in (data.get("webPages", {}) or {}).get("value", [])[:max_results]:
                results.append({
                    "title": item.get("name", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("snippet", ""),
                    "source": "bing"
                })
            return results
        except Exception as e:
            logger.error(f"Bing search failed: {e}")
            return []

class TavilyProvider(WebSearchProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://api.tavily.com/search"

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        payload = {
            "query": query,
            "max_results": max_results,
        }

        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(self.endpoint, json=payload, headers=headers, timeout=10.0)
                r.raise_for_status()
                data = r.json()

            results = []
            for item in data.get("results", []):
                results.append({
                    "title": item.get("title") or item.get("name") or "",
                    "url": item.get("url") or item.get("link") or "",
                    "snippet": item.get("snippet") or item.get("content") or "",
                    "source": "tavily"
                })
            return results
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return []

class GoogleProvider(WebSearchProvider):
    def __init__(self, api_key: str, cx: str):
        self.api_key = api_key
        self.cx = cx
        self.endpoint = "https://www.googleapis.com/customsearch/v1"

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        if not self.api_key or not self.cx:
            return []
            
        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "num": max(1, min(max_results, 10)),
        }

        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(self.endpoint, params=params, timeout=10.0)
                r.raise_for_status()
                data = r.json()

            results = []
            for item in data.get("items", [])[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "source": "google"
                })
            return results
        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return []
