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

def load_settings(env_file: Optional[Path] = None, override_environ: bool = False) -> Settings:
    """Load settings from environment variables and optional env file."""
    if env_file:
        load_dotenv(dotenv_path=env_file, override=override_environ)
        
    return Settings(
        app_name=os.environ.get("APP_NAME", "JARVISv4"),
        version=os.environ.get("APP_VERSION", "0.1.0"),
        debug=os.environ.get("DEBUG", "false").lower() == "true",
        memory_store_type=os.environ.get("MEMORY_STORE_TYPE", "memory"),
        memory_db_path=Path(os.environ.get("MEMORY_DB_PATH", "data/memory.db"))
    )
