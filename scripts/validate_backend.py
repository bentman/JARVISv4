import sys
import subprocess
import warnings
import os
from datetime import datetime, timedelta
from pathlib import Path

class ValidationLogger:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_dir = Path("reports")
        self.report_dir.mkdir(exist_ok=True)
        self.report_file = self.report_dir / f"backend_validation_report_{self.timestamp}.txt"
        self.buffer = []
    
    def log(self, msg, console=True):
        if console:
            print(msg)
        self.buffer.append(msg)

    def save(self):
        with open(self.report_file, "w", encoding="utf-8") as f:
            f.write("\n".join(self.buffer))
        print(f"Report saved to: {self.report_file}")

def cleanup_old_reports(logger):
    """Remove reports older than 14 days based on file modification time"""
    cutoff = datetime.now() - timedelta(days=14)
    removed = 0
    if not logger.report_dir.exists():
        return
    
    for report in logger.report_dir.glob("backend_validation_report_*.txt"):
        mtime = datetime.fromtimestamp(report.stat().st_mtime)
        if mtime < cutoff:
            report.unlink()
            removed += 1
    if removed > 0:
        logger.log(f"Cleanup: Removed {removed} old reports (>14 days).", console=False)

def check_venv_health(logger):
    """Verify venv Python can execute and return version"""
    venv_python = Path("backend/.venv/Scripts/python.exe")
    if not venv_python.exists():
        logger.log(f"[FAIL] Venv Python not found at {venv_python}")
        return False, "Missing"
    
    try:
        result = subprocess.run(
            [str(venv_python), "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            logger.log(f"[PASS] Venv Python Health: {version}")
            return True, version
        else:
            logger.log(f"[FAIL] Venv Python failed with exit code {result.returncode}")
            return False, "Execution Error"
    except Exception as e:
        logger.log(f"[FAIL] Venv Python Health Check Error: {e}")
        return False, str(e)

def main():
    logger = ValidationLogger()
    cleanup_old_reports(logger)
    
    logger.log("JARVISv4 Backend Validation Harness")
    logger.log("===================================")
    
    root = Path(".")
    failures = []
    
    # Capture Python warnings
    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always")
        
        # Path Checks
        checks = [
            ("backend/main.py", True),
            ("backend/requirements.txt", True),
            ("backend/.venv", True),
            ("tests", False),
            ("frontend", False)
        ]
        
        for path_str, is_critical in checks:
            path = root / path_str
            if path.exists():
                logger.log(f"[PASS] {path_str} found")
            else:
                if is_critical:
                    logger.log(f"[FAIL] {path_str} MISSING")
                    failures.append(path_str)
                else:
                    logger.log(f"[WARN] {path_str} missing (optional)")

        # Venv Health Check
        health_ok, version = check_venv_health(logger)
        if not health_ok:
            failures.append("Venv Health")

    # Deprecation Reporting
    deprecations = [w for w in captured_warnings if issubclass(w.category, DeprecationWarning)]
    unique_deprecations = {(w.message, w.filename, w.lineno) for w in deprecations}
    
    logger.log("===================================")
    logger.log(f"Deprecation Warnings: Total={len(deprecations)}, Unique={len(unique_deprecations)}")
    
    if unique_deprecations:
        logger.log("Top 3 unique deprecations:", console=True)
        for i, (msg, fname, line) in enumerate(list(unique_deprecations)[:3]):
            logger.log(f"  {i+1}. {msg} ({fname}:{line})", console=True)
        
        # Log all to report
        if len(unique_deprecations) > 3:
            logger.log("All unique deprecations:", console=False)
            for i, (msg, fname, line) in enumerate(unique_deprecations):
                logger.log(f"  {i+1}. {msg} ({fname}:{line})", console=False)

    logger.log("===================================")
    if failures:
        logger.log(f"Validation FAILED. Missing/Broken: {failures}")
        logger.save()
        sys.exit(1)
    
    logger.log("Validation PASSED.")
    logger.save()
    sys.exit(0)

if __name__ == "__main__":
    main()
