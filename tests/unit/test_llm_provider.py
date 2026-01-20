import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from openai import APITimeoutError, RateLimitError
from backend.core.llm.provider import OpenAIProvider, LLMProviderError

@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.llm_model = "test-model"
    settings.llm_api_key = "test-key"
    settings.llm_base_url = "http://test-url"
    return settings

@pytest.mark.asyncio
async def test_openai_provider_initialization():
    provider = OpenAIProvider(model="gpt-4o", api_key="key", base_url="http://url")
    assert provider.model == "gpt-4o"
    assert provider.client.api_key == "key"
    assert str(provider.client.base_url).rstrip("/") == "http://url"
    await provider.close()

@pytest.mark.asyncio
async def test_openai_provider_generate_success():
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="Test response"))
    ]
    
    with patch("openai.resources.chat.completions.AsyncCompletions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        
        provider = OpenAIProvider(model="gpt-4o")
        result = await provider.generate("Hello")
        
        assert result == "Test response"
        mock_create.assert_called_once()
        args, kwargs = mock_create.call_args
        assert kwargs["model"] == "gpt-4o"
        assert kwargs["messages"] == [{"role": "user", "content": "Hello"}]
        await provider.close()

@pytest.mark.asyncio
async def test_openai_provider_retry_logic():
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="Success after retry"))
    ]
    
    with patch("openai.resources.chat.completions.AsyncCompletions.create", new_callable=AsyncMock) as mock_create:
        # Fail twice, then succeed
        mock_create.side_effect = [
            RateLimitError(message="Rate limit", response=MagicMock(), body=None),
            APITimeoutError(request=MagicMock()),
            mock_response
        ]
        
        provider = OpenAIProvider(model="gpt-4o", max_retries=3)
        
        # Patch sleep to speed up test
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await provider.generate("Hello")
            
            assert result == "Success after retry"
            assert mock_create.call_count == 3
            assert mock_sleep.call_count == 2
        await provider.close()

@pytest.mark.asyncio
async def test_openai_provider_max_retries_reached():
    with patch("openai.resources.chat.completions.AsyncCompletions.create", new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = APITimeoutError(request=MagicMock())
        
        provider = OpenAIProvider(model="gpt-4o", max_retries=2)
        
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(LLMProviderError, match="after 2 attempts"):
                await provider.generate("Hello")
        await provider.close()

@pytest.mark.asyncio
async def test_openai_provider_empty_response():
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content=None))
    ]
    
    with patch("openai.resources.chat.completions.AsyncCompletions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        
        provider = OpenAIProvider(model="gpt-4o")
        with pytest.raises(LLMProviderError, match="empty response"):
            await provider.generate("Hello")
        await provider.close()
