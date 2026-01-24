import argparse
from typing import Any, Dict

from backend.core.controller import ECFController
from backend.main import _resolve_settings


def test_cli_llm_overrides(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:1/v1")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")

    args = argparse.Namespace(
        env_file=None,
        llm_base_url="http://localhost:11434/v1",
        llm_model="llama3.1:8b",
        llm_api_key=None,
        llm_timeout_seconds=7.0,
        llm_max_retries=0
    )
    settings = _resolve_settings(args)

    captured: Dict[str, Any] = {}

    class SpyProvider:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        async def close(self):
            return None

    monkeypatch.setattr("backend.core.controller.OpenAIProvider", SpyProvider)

    controller = ECFController(
        settings=settings,
        llm_timeout_seconds=args.llm_timeout_seconds,
        llm_max_retries=args.llm_max_retries
    )

    assert captured["base_url"] == "http://localhost:11434/v1"
    assert captured["model"] == "llama3.1:8b"
    assert captured["timeout"] == 7.0
    assert captured["max_retries"] == 0
    assert controller.settings.llm_base_url == "http://localhost:11434/v1"
    assert controller.settings.llm_model == "llama3.1:8b"