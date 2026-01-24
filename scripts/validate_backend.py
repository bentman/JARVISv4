"""
JARVISv4 Backend Validation Suite
Single comprehensive validation that runs all backend tests and generates timestamped reports.
Aligned to legacy v3 harness behavior for reporting and execution.
"""
import sys
import os
import subprocess
import xml.etree.ElementTree as ET
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path


def get_venv_python_path() -> Path:
    """Get the path to the Python executable in the virtual environment"""
    base_path = Path("backend")
    venv_path = base_path / ".venv"
    
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"
    
    return python_exe


class ValidationLogger:
    """Handles terminal output and file-based reporting"""
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_dir = Path("reports")
        self.report_dir.mkdir(exist_ok=True)
        self.report_file = self.report_dir / f"backend_validation_report_{self.timestamp}.txt"
        self.buffer = []
        
        self.log(f"JARVISv4 Backend Validation Session started at {datetime.now().isoformat()}")
        self.log(f"Report File: {self.report_file}")
        self.log("="*60)

    def log(self, message: str):
        print(message)
        self.buffer.append(message)
    
    def header(self, title: str):
        self.log("\n" + "="*60)
        self.log(title.upper())
        self.log("="*60)

    def save(self):
        with open(self.report_file, "w", encoding="utf-8") as f:
            f.write("\n".join(self.buffer))
        print(f"\n[SUCCESS] Report saved to {self.report_file}")


def validate_venv(logger) -> bool:
    """Validate that the virtual environment exists and is valid"""
    venv_python = get_venv_python_path()
    
    if not venv_python.exists():
        logger.log(f"ERROR: Virtual environment not found at: {venv_python}")
        logger.log("Please ensure the venv is created at backend/.venv")
        return False
    
    try:
        result = subprocess.run(
            [str(venv_python), "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            logger.log(f"ERROR: Virtual environment Python is not working: {result.stderr}")
            return False
        else:
            logger.log(f"SUCCESS: Using Python interpreter: {venv_python} ({result.stdout.strip()})")
            return True
    except subprocess.TimeoutExpired:
        logger.log("ERROR: Virtual environment Python timed out during version check")
        return False
    except Exception as e:
        logger.log(f"ERROR: Error accessing virtual environment Python: {e}")
        return False


def extract_deprecation_warnings(stderr: str) -> list[str]:
    """Extract deprecation warnings from stderr output"""
    warnings = []
    if not stderr:
        return warnings

    lines = stderr.split('\n')
    for line in lines:
        line = line.strip()
        if any(w in line for w in ['DeprecationWarning', 'FutureWarning', 'PendingDeprecationWarning']):
            warnings.append(line)
    return warnings


def parse_junit_xml(xml_file: Path) -> tuple[list[tuple[str, str]], str, bool, bool]:
    """Parse JUnit XML file and return (test_results, summary, success, has_skips)"""
    if not xml_file.exists():
        return [], "No XML report generated", False, False

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        test_results = []
        total_tests = 0
        failures = 0
        errors = 0
        skipped = 0

        # Parse test cases
        for testsuite in root:
            for testcase in testsuite:
                total_tests += 1
                test_name = f"{testcase.get('classname', '')}::{testcase.get('name', '')}"

                if testcase.find('failure') is not None:
                    test_results.append(('FAIL', test_name))
                    failures += 1
                elif testcase.find('error') is not None:
                    test_results.append(('ERROR', test_name))
                    errors += 1
                elif testcase.find('skipped') is not None:
                    test_results.append(('SKIP', test_name))
                    skipped += 1
                else:
                    test_results.append(('PASS', test_name))

        # Build summary
        summary_parts = []
        if total_tests > 0:
            summary_parts.append(f"{total_tests} tests")
        if failures > 0:
            summary_parts.append(f"{failures} failed")
        if errors > 0:
            summary_parts.append(f"{errors} errors")
        if skipped > 0:
            summary_parts.append(f"{skipped} skipped")

        summary = ", ".join(summary_parts) if summary_parts else "No tests collected"
        success = (failures == 0 and errors == 0)
        has_skips = skipped > 0

        return test_results, summary, success, has_skips

    except Exception as e:
        return [], f"XML parsing error: {e}", False, False


def run_pytest_on_directory(logger, category_name: str, test_dir: str) -> tuple[str, str]:
    """Run pytest on a directory of tests with per-test visibility using JUnit XML"""
    logger.header(f"{category_name} Tests")

    dir_path = Path(test_dir)
    if not dir_path.exists():
        logger.log(f"WARN: Directory {test_dir} not found. Skipping category.")
        return 'WARN', 'Directory not found'

    venv_python = get_venv_python_path()
    xml_file = Path(f"test_results_{category_name.lower()}_{datetime.now().strftime('%H%M%S')}.xml")

    try:
        result = subprocess.run(
            [str(venv_python), "-m", "pytest", test_dir, "--junitxml", str(xml_file), "--tb=no", "-q"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=300
        )

        test_results, summary, xml_success, has_skips = parse_junit_xml(xml_file)

        for status, test_name in test_results:
            status_icon = {'PASS': '✓', 'FAIL': '✗', 'SKIP': '○', 'ERROR': '✗'}.get(status, '?')
            logger.log(f"  {status_icon} {status}: {test_name}")

        # Summary line for category
        if xml_success and result.returncode in [0, 5]: # 0=Pass, 5=No tests
            if has_skips:
                status = 'PASS_WITH_SKIPS'
                logger.log(f"PASS WITH SKIPS: {category_name}: {summary}")
            else:
                status = 'PASS'
                logger.log(f"SUCCESS: {category_name}: {summary}")
            
            # Check for deprecation warnings in stderr
            warnings = extract_deprecation_warnings(result.stderr or "")
            if warnings:
                logger.log(f"DEPRECATION WARNINGS DETECTED: {len(warnings)} counts")
            
            return status, summary
        else:
            logger.log(f"FAILED: {category_name}: {summary}")
            if result.stderr and not test_results:
                logger.log(result.stderr.strip())
            return 'FAIL', summary

    except Exception as e:
        logger.log(f"FAILED: {category_name}: Unexpected error - {e}")
        return 'FAIL', str(e)
    finally:
        if xml_file.exists():
            xml_file.unlink()


def cleanup_old_reports(logger):
    """Remove validation reports older than 14 days based on filename timestamp"""
    report_dir = Path("reports")
    if not report_dir.exists():
        return

    now = datetime.now()
    cutoff = now - timedelta(days=14)
    removed_count = 0

    for report_file in report_dir.glob("backend_validation_report_*.txt"):
        try:
            filename = report_file.name
            timestamp_str = filename.replace("backend_validation_report_", "").replace(".txt", "")
            file_datetime = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

            if file_datetime < cutoff:
                report_file.unlink()
                removed_count += 1
                logger.log(f"Cleaned up old report: {report_file.name}")
        except (ValueError, OSError):
            continue

    if removed_count > 0:
        logger.log(f"Report cleanup: Removed {removed_count} reports older than 14 days")


def probe_api_endpoints(logger) -> bool:
    """Start API process and verify /healthz and /metrics respond"""
    venv_python = get_venv_python_path()
    api_host = "127.0.0.1"
    api_port = 8001
    base_url = f"http://{api_host}:{api_port}"
    proc = None

    logger.header("API Process Smoke Probe")
    logger.log(
        "API_SMOKE_STARTING cmd=python -m uvicorn backend.api.app:app "
        f"port={api_port}"
    )

    try:
        proc = subprocess.Popen(
            [
                str(venv_python),
                "-m",
                "uvicorn",
                "backend.api.app:app",
                "--host",
                api_host,
                "--port",
                str(api_port)
            ],
            cwd=Path.cwd(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True
        )

        deadline = time.time() + 10
        healthz_url = f"{base_url}/healthz"
        healthz_ok = False

        while time.time() < deadline:
            try:
                with urllib.request.urlopen(healthz_url, timeout=2) as response:
                    if response.status == 200:
                        body = response.read().decode("utf-8")
                        if "\"status\":\"ok\"" in body:
                            healthz_ok = True
                            break
            except Exception:
                time.sleep(0.25)

        if not healthz_ok:
            logger.log(f"API_SMOKE=FAIL reason=healthz_unreachable url={healthz_url}")
            return False

        logger.log(f"API_HEALTHZ_OK url={healthz_url}")

        metrics_url = f"{base_url}/metrics"
        try:
            with urllib.request.urlopen(metrics_url, timeout=2) as response:
                if response.status != 200:
                    logger.log(f"API_SMOKE=FAIL reason=metrics_status_{response.status} url={metrics_url}")
                    return False
                metrics_body = response.read().decode("utf-8")
        except Exception as exc:
            logger.log(f"API_SMOKE=FAIL reason=metrics_error url={metrics_url} error={exc}")
            return False

        if "# HELP jarvis_requests_total" not in metrics_body:
            logger.log(f"API_SMOKE=FAIL reason=metrics_missing_header url={metrics_url}")
            return False

        logger.log("API_METRICS_OK contains=\"# HELP jarvis_requests_total\"")
        logger.log("API_SMOKE=PASS")
        return True
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def main():
    """Main validation function"""
    logger = ValidationLogger()
    cleanup_old_reports(logger)

    if not validate_venv(logger):
        logger.log("!!! CRITICAL ERROR: Virtual environment validation failed.")
        logger.save()
        return 1

    api_smoke_ok = probe_api_endpoints(logger)
    if not api_smoke_ok:
        logger.log("!!! CRITICAL ERROR: API smoke probe failed.")
        logger.save()
        return 1

    # Run tests by category
    unit_status, _ = run_pytest_on_directory(logger, "Unit", "tests/unit")
    integration_status, _ = run_pytest_on_directory(logger, "Integration", "tests/integration")
    agentic_status, _ = run_pytest_on_directory(logger, "Agentic", "tests/agentic")

    # Summary
    logger.header("Backend Validation Summary")
    logger.log(f"Unit Tests:        {unit_status}")
    logger.log(f"Integration Tests: {integration_status}")
    logger.log(f"Agentic Tests:     {agentic_status}")
    logger.log("="*60)

    # Invariant Summary (Machine Readable)
    logger.log("\n[INVARIANTS]")
    logger.log(f"UNIT_TESTS={unit_status}")
    logger.log(f"INTEGRATION_TESTS={integration_status}")
    logger.log(f"AGENTIC_TESTS={agentic_status}")

    statuses = [unit_status, integration_status, agentic_status]
    has_any_fail = any(s == 'FAIL' for s in statuses)
    has_any_skips = any(s == 'PASS_WITH_SKIPS' for s in statuses)

    if not has_any_fail:
        if has_any_skips:
            logger.log("\n✅ JARVISv4 Current ./backend is VALIDATED WITH EXPECTED SKIPS!")
        else:
            logger.log("\n✅ JARVISv4 Current ./backend is validated!")
        status = 0
    else:
        logger.log("\n!!! Validation failed - see specific component failures above")
        status = 1

    logger.save()
    return status


if __name__ == "__main__":
    sys.exit(main())
