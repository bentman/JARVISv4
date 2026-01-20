import asyncio
import sys
import respx
import json
import logging
from httpx import Response
from backend.core.llm.provider import OpenAIProvider

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_connectivity():
    """
    Smoke test to verify LLMProvider connectivity and handshake.
    Uses respx to simulate a local Ollama/vLLM endpoint.
    """
    logger.info("Starting LLM Connectivity Smoke Test...")
    
    base_url = "http://localhost:11434/v1"
    model = "llama3"
    
    # Define the mock response
    mock_response = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Handshake Successful. I am ready.",
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 9,
            "completion_tokens": 12,
            "total_tokens": 21
        }
    }

    async with respx.mock(base_url=base_url, assert_all_called=False) as respx_mock:
        # Mock the chat completions endpoint
        respx_mock.post("/chat/completions").mock(return_value=Response(200, json=mock_response))
        
        logger.info(f"Connecting to mock endpoint: {base_url}")
        provider = OpenAIProvider(
            model=model,
            base_url=base_url,
            api_key="ollama", # Ollama usually ignores the key
            max_retries=1
        )
        
        try:
            logger.info("Sending handshake prompt...")
            response = await provider.generate("Handshake check")
            
            logger.info(f"Received Response: {response}")
            
            if "Successful" in response:
                logger.info("✅ SMOKE TEST PASSED: Handshake verified.")
                return True
            else:
                logger.error("❌ SMOKE TEST FAILED: Unexpected response content.")
                return False
                
        except Exception as e:
            logger.error(f"❌ SMOKE TEST FAILED: Connection error: {str(e)}")
            return False
        finally:
            await provider.close()

if __name__ == "__main__":
    success = asyncio.run(test_connectivity())
    if not success:
        sys.exit(1)
