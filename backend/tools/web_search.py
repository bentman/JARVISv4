"""
Unified Web Search tool for JARVISv4.
Integrates with multiple providers to provide external knowledge to agents.
"""
import logging
import json
from typing import Any, Dict, List, Optional

from backend.tools.base import BaseTool, ToolDefinition
from backend.core.cache import RedisCache
from backend.core.search_providers import (
    WebSearchProvider, 
    DuckDuckGoProvider, 
    BingProvider, 
    TavilyProvider,
    GoogleProvider
)
from backend.core.config.settings import load_settings
from backend.core.privacy import PrivacyService
from backend.core.budget import BudgetService

logger = logging.getLogger(__name__)

class WebSearchTool(BaseTool):
    """
    Tool for performing web searches across multiple providers.
    """

    def __init__(self, settings=None):
        self.settings = settings or load_settings()
        
        # Initialize Safety Services
        self.privacy = PrivacyService(
            secret_key=self.settings.privacy_secret_key,
            salt=self.settings.privacy_salt,
            redaction_level=self.settings.privacy_redaction_level
        )
        self.budget = BudgetService(self.settings)
        self.cache: Optional[RedisCache] = None
        if self.settings.redis_url:
            self.cache = RedisCache(self.settings.redis_url)

        self._definition = ToolDefinition(
            name="web_search",
            description="Search the web for real-time information, news, or facts.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to execute."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return.",
                        "default": 5
                    },
                    "provider": {
                        "type": "string",
                        "description": "The search provider to use (duckduckgo, bing, tavily).",
                        "default": "duckduckgo"
                    }
                },
                "required": ["query"]
            }
        )
        # Initialize providers
        self.providers: Dict[str, WebSearchProvider] = {
            "duckduckgo": DuckDuckGoProvider()
        }
        
        if self.settings.search_bing_api_key:
            self.providers["bing"] = BingProvider(self.settings.search_bing_api_key)
        if self.settings.search_tavily_api_key:
            self.providers["tavily"] = TavilyProvider(self.settings.search_tavily_api_key)
        if self.settings.search_google_api_key and self.settings.search_google_cx:
            self.providers["google"] = GoogleProvider(
                self.settings.search_google_api_key, 
                self.settings.search_google_cx
            )

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    async def execute(self, **kwargs) -> Any:
        """Execute the web search."""
        raw_query = kwargs.get("query")
        if not raw_query:
            raise ValueError("Query parameter is required for web_search tool")
            
        max_results = kwargs.get("max_results", 5)
        provider = kwargs.get("provider", "duckduckgo")

        # 1. Privacy Redaction (Inbound)
        query = self.privacy.redact(raw_query)
        if query != raw_query:
            logger.info("Search query was redacted for privacy.")

        # 2. Provider Selection
        target_provider = provider.lower()
        if target_provider not in self.providers:
            logger.warning(f"Provider {provider} not available. Falling back to duckduckgo.")
            target_provider = "duckduckgo"
            
        # 3. Budget Check
        # Estimate cost: 1 unit per search (arbitrary baseline)
        if not self.budget.check_availability("search", 1.0):
            return "ERROR: Search operation blocked by budget limit."

        cache_key = f"web_search:{target_provider}:{max_results}:{query}"
        if self.cache:
            cached_payload = self.cache.get_json(cache_key)
            if cached_payload is not None:
                return json.dumps(cached_payload, indent=2)

        prov = self.providers[target_provider]
        
        logger.info(f"Executing web search with {target_provider}: {query}")
        results = await prov.search(query, max_results=max_results)
        
        # 4. Budget Recording
        if results:
            self.budget.record_spend("search", 1.0, item_id=f"web_search:{target_provider}")

        if not results:
            return "No results found for the query."

        if self.cache:
            self.cache.set_json(cache_key, results)

        # 5. Privacy Redaction (Outbound)
        # Redact snippets in results to ensure no PII is returned to the agent context
        for item in results:
            if "snippet" in item:
                item["snippet"] = self.privacy.redact(item["snippet"])
            
        return json.dumps(results, indent=2)
