import sys
import subprocess
from pathlib import Path

def test_backend_main_execution():
    """Test that backend/main.py runs and prints the initialization message."""
    repo_root = Path(__file__).parent.parent.parent
    main_script = repo_root / "backend" / "main.py"
    
    # Use the current python interpreter (venv) with repo root in PYTHONPATH
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)
    
    # Pass through LLM settings to satisfy config requirements in main.py
    env["LLM_BASE_URL"] = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
    env["LLM_MODEL"] = os.environ.get("LLM_MODEL", "llama3.1:8b")

    result = subprocess.run(
        [sys.executable, str(main_script)],
        capture_output=True,
        text=True,
        timeout=5,
        env=env
    )
    
    assert result.returncode == 0
    assert "JARVISv4 Backend initialized." in result.stdout
    assert result.stderr == ""
