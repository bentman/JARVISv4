import sys
import subprocess
from pathlib import Path

def test_backend_main_execution():
    """Test that backend/main.py runs and prints the initialization message."""
    repo_root = Path(__file__).parent.parent.parent
    main_script = repo_root / "backend" / "main.py"
    
    # Use the current python interpreter (venv)
    result = subprocess.run(
        [sys.executable, str(main_script)],
        capture_output=True,
        text=True,
        timeout=5
    )
    
    assert result.returncode == 0
    assert "JARVISv4 Backend initialized." in result.stdout
    assert result.stderr == ""
