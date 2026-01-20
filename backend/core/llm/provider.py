import asyncio
import logging
from typing import Any, Dict, Optional
from openai import AsyncOpenAI, APIError, APITimeoutError, APIConnectionError, RateLimitError

from backend.core.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    pass

class OpenAIProvider(BaseLLMProvider):
    """
    LLM provider using the OpenAI client.
    Compatible with OpenAI, Azure, and local providers (Ollama, vLLM).
    """
    
    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3
    ):
        self.model = model
        self.max_retries = max_retries
        
        # Initialize AsyncOpenAI client
        # If base_url is None, it defaults to standard OpenAI API
        self.client = AsyncOpenAI(
            api_key=api_key or "sk-no-key-required", # Default to template key if not provided
            base_url=base_url,
            timeout=timeout
        )
        
        logger.info(f"OpenAIProvider initialized with model={model}, base_url={base_url}")

    async def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text response with exponential backoff retries.
        """
        attempt = 0
        last_error = None
        
        while attempt < self.max_retries:
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    **kwargs
                )
                
                content = response.choices[0].message.content
                if content is None:
                    raise LLMProviderError("LLM returned empty response")
                    
                return content.strip()
                
            except (APITimeoutError, APIConnectionError, RateLimitError) as e:
                attempt += 1
                last_error = e
                if attempt >= self.max_retries:
                    break
                    
                wait_time = 2 ** attempt # Exponential backoff
                logger.warning(f"LLM request failed (attempt {attempt}/{self.max_retries}): {str(e)}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                
            except APIError as e:
                logger.error(f"OpenAI API error: {str(e)}")
                raise LLMProviderError(f"OpenAI API error: {str(e)}") from e
                
            except Exception as e:
                logger.error(f"Unexpected error in OpenAIProvider: {str(e)}")
                raise LLMProviderError(f"Unexpected error: {str(e)}") from e
                
        raise LLMProviderError(f"LLM request failed after {self.max_retries} attempts. Last error: {str(last_error)}")

    async def close(self):
        """Close the underlying client session."""
        await self.client.close()
