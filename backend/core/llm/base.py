from abc import ABC, abstractmethod

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate a text response from the given prompt.
        
        Args:
            prompt: The input text prompt.
            **kwargs: Additional provider-specific arguments (temperature, max_tokens, etc.)
            
        Returns:
            The generated text response.
        """
        pass
