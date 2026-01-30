import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

@dataclass(frozen=True)
class Settings:
    app_name: str = "JARVISv4"
    version: str = "0.1.0"
    debug: bool = False
    
    # Memory Settings
    memory_store_type: str = "memory"  # Options: "memory", "sqlite"
    memory_db_path: Path = Path("data/memory.db")
    working_storage_path: Path = Path("tasks")

    # LLM Settings
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    llm_base_url: Optional[str] = None
    llm_api_key: Optional[str] = None
    
    # Privacy Settings (ECF Tier 4)
    privacy_secret_key: str = "dev-secret-do-not-use-in-production-12345"
    privacy_salt: str = "v4-salt-static"
    privacy_redaction_level: str = "partial"  # options: none, partial, strict

    # Budget Settings
    budget_enforcement_level: str = "log"  # none, log, block
    budget_limits: Optional[dict] = None  # Dict of category: limit
    budget_db_path: Path = Path("data/budget.db")

    # Search Settings
    search_bing_api_key: Optional[str] = None
    search_tavily_api_key: Optional[str] = None
    search_google_api_key: Optional[str] = None
    search_google_cx: Optional[str] = None
    redis_url: Optional[str] = None

    # Model Provisioning Policy
    model_provisioning_policy: str = "strict"  # strict, on_demand, startup

    # API Settings
    api_host: str = "127.0.0.1"
    api_port: int = 8000

def load_settings(env_file: Optional[Path] = None, override_environ: bool = False) -> Settings:
    """Load settings from environment variables and optional env file."""
    if env_file:
        load_dotenv(dotenv_path=env_file, override=override_environ)
        
    return Settings(
        app_name=os.environ.get("APP_NAME", "JARVISv4"),
        version=os.environ.get("APP_VERSION", "0.1.0"),
        debug=os.environ.get("DEBUG", "false").lower() == "true",
        memory_store_type=os.environ.get("MEMORY_STORE_TYPE", "memory"),
        memory_db_path=Path(os.environ.get("MEMORY_DB_PATH", "data/memory.db")),
        working_storage_path=Path(os.environ.get("WORKING_STORAGE_PATH", "tasks")),
        llm_provider=os.environ.get("LLM_PROVIDER", "openai"),
        llm_model=os.environ.get("LLM_MODEL", "gpt-4o"),
        llm_base_url=os.environ.get("LLM_BASE_URL"),
        llm_api_key=os.environ.get("LLM_API_KEY"),
        privacy_secret_key=os.environ.get("PRIVACY_SECRET_KEY", "dev-secret-do-not-use-in-production-12345"),
        privacy_salt=os.environ.get("PRIVACY_SALT", "v4-salt-static"),
        privacy_redaction_level=os.environ.get("PRIVACY_REDACTION_LEVEL", "partial"),
        budget_enforcement_level=os.environ.get("BUDGET_ENFORCEMENT_LEVEL", "log"),
        budget_limits=eval(os.environ.get("BUDGET_LIMITS", "{}")),  # Using eval for simplicity in parsing dict from env
        budget_db_path=Path(os.environ.get("BUDGET_DB_PATH", "data/budget.db")),
        search_bing_api_key=os.environ.get("SEARCH_BING_API_KEY"),
        search_tavily_api_key=os.environ.get("SEARCH_TAVILY_API_KEY"),
        search_google_api_key=os.environ.get("SEARCH_GOOGLE_API_KEY"),
        search_google_cx=os.environ.get("SEARCH_GOOGLE_CX"),
        redis_url=os.environ.get("REDIS_URL"),
        model_provisioning_policy=os.environ.get("MODEL_PROVISIONING_POLICY", "strict"),
        api_host=os.environ.get("API_HOST", "127.0.0.1"),
        api_port=int(os.environ.get("API_PORT", "8000"))
    )
