import os
from backend.core.config import load_settings

def test_load_from_env_file(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("APP_NAME=EnvFileApp\nDEBUG=true")
    
    settings = load_settings(env_file=env_file)
    assert settings.app_name == "EnvFileApp"
    assert settings.debug is True

def test_precedence_env_var_wins_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_NAME", "SystemApp")
    env_file = tmp_path / ".env"
    env_file.write_text("APP_NAME=EnvFileApp")
    
    settings = load_settings(env_file=env_file)
    # By default override_environ=False, so SystemApp wins
    assert settings.app_name == "SystemApp"

def test_override_env_file_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_NAME", "SystemApp")
    env_file = tmp_path / ".env"
    env_file.write_text("APP_NAME=EnvFileApp")
    
    settings = load_settings(env_file=env_file, override_environ=True)
    # With override_environ=True, EnvFileApp wins
    assert settings.app_name == "EnvFileApp"
