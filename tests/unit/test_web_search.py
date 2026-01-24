import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from backend.tools.web_search import WebSearchTool
from backend.core.config.settings import Settings

@pytest.fixture
def mock_settings():
    return Settings(
        privacy_secret_key="test-secret",
        privacy_salt="test-salt",
        privacy_redaction_level="partial",
        budget_enforcement_level="none",
        search_bing_api_key="fake-bing",
        search_tavily_api_key="fake-tavily"
    )

@pytest.mark.asyncio
async def test_web_search_tool_initialization(mock_settings):
    with patch('backend.tools.web_search.load_settings', return_value=mock_settings):
        tool = WebSearchTool()
        assert "duckduckgo" in tool.providers
        assert "bing" in tool.providers
        assert "tavily" in tool.providers

@pytest.mark.asyncio
async def test_web_search_privacy_redaction(mock_settings):
    # Mock DDG provider to avoid network
    with patch('backend.tools.web_search.DuckDuckGoProvider') as mock_ddg_class:
        mock_ddg = mock_ddg_class.return_value
        mock_ddg.search = AsyncMock(return_value=[{"title": "Result", "url": "http://test.com", "snippet": "Found info"}])
        
        with patch('backend.tools.web_search.load_settings', return_value=mock_settings):
            tool = WebSearchTool()
            
            # Test inbound redaction (Email)
            query_with_email = "Search for user@example.com info"
            await tool.execute(query=query_with_email)
            
            # Verify the provider received redacted query
            # Wait, tool.execute calls self.privacy.redact(raw_query)
            mock_ddg.search.assert_called()
            called_query = mock_ddg.search.call_args[0][0]
            assert "user@example.com" not in called_query
            assert "[EMAIL_REDACTED]" in called_query

@pytest.mark.asyncio
async def test_web_search_budget_block(mock_settings):
    # Set budget to block
    blocking_settings = Settings(
        budget_enforcement_level="block",
        budget_limits={"search": 0.5}, # Low limit
        budget_db_path=mock_settings.budget_db_path
    )
    
    with patch('backend.tools.web_search.load_settings', return_value=blocking_settings):
        # We need to mock the budget service specifically to simulate being out of budget
        with patch('backend.tools.web_search.BudgetService') as mock_budget_class:
            mock_budget = mock_budget_class.return_value
            mock_budget.check_availability.return_value = False
            
            tool = WebSearchTool()
            result = await tool.execute(query="test")
            
            assert "blocked by budget limit" in result
            mock_budget.check_availability.assert_called_with("search", 1.0)

@pytest.mark.asyncio
async def test_web_search_provider_fallback(mock_settings):
    with patch('backend.tools.web_search.load_settings', return_value=mock_settings):
        with patch('backend.tools.web_search.DuckDuckGoProvider') as mock_ddg_class:
            mock_ddg = mock_ddg_class.return_value
            mock_ddg.search = AsyncMock(return_value=[{"title": "DDG Result"}])
            
            tool = WebSearchTool()
            # Request non-existent provider
            await tool.execute(query="test", provider="unknown_service")
            
            # Should fallback to duckduckgo
            mock_ddg.search.assert_called()


@pytest.mark.asyncio
async def test_web_search_uses_cache(mock_settings):
    cached_results = [{"title": "Cached Result", "url": "http://cached"}]
    cache_settings = Settings(
        privacy_secret_key=mock_settings.privacy_secret_key,
        privacy_salt=mock_settings.privacy_salt,
        privacy_redaction_level=mock_settings.privacy_redaction_level,
        budget_enforcement_level=mock_settings.budget_enforcement_level,
        search_bing_api_key=mock_settings.search_bing_api_key,
        search_tavily_api_key=mock_settings.search_tavily_api_key,
        redis_url="redis://localhost:6379/0"
    )

    with patch('backend.tools.web_search.RedisCache') as mock_cache_class:
        mock_cache = mock_cache_class.return_value
        mock_cache.get_json.return_value = cached_results

        with patch('backend.tools.web_search.load_settings', return_value=cache_settings):
            tool = WebSearchTool()

            with patch('backend.tools.web_search.DuckDuckGoProvider') as mock_ddg_class:
                mock_ddg = mock_ddg_class.return_value
                mock_ddg.search = AsyncMock()

                result = await tool.execute(query="cache test", provider="duckduckgo")

                assert json.loads(result) == cached_results
                mock_cache.get_json.assert_called_once()
                mock_ddg.search.assert_not_called()
