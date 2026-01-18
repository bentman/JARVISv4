import os
from backend.core.config import load_settings, Settings

def test_default_settings():
    settings = load_settings()
    assert isinstance(settings, Settings)
    assert settings.app_name == "JARVISv4"
    assert settings.debug is False

def test_env_override(monkeypatch):
    monkeypatch.setenv("APP_NAME", "TestApp")
    monkeypatch.setenv("DEBUG", "true")
    settings = load_settings()
    assert settings.app_name == "TestApp"
    assert settings.debug is True
