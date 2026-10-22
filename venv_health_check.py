#!/usr/bin/env python3
"""
venv health check — detects Python version mismatch and auto-rebuilds venv.
Runs periodically (every 6 hours) via LaunchAgent to catch Python upgrades
even when the process is sleeping or not restarted.
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).parent
VENV_PATH = REPO_ROOT / ".venv"
LOG_FILE = Path.home() / ".rto_tracker" / "venv_health_check.log"


def log(msg: str):
    """Log to file with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp} {msg}\n")
    print(msg)


def get_system_python_version() -> str:
    """Get the active Python version from /usr/bin/env python3."""
    result = subprocess.run(["/usr/bin/env", "python3", "--version"],
                          capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        return result.stdout.strip()  # e.g., "Python 3.14.8"
    return "unknown"


def get_venv_python_version() -> str:
    """Get the venv Python version."""
    venv_python = VENV_PATH / "bin" / "python3"
    if not venv_python.exists():
        return "venv not found"
    result = subprocess.run([str(venv_python), "--version"],
                          capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        return result.stdout.strip()
    return "unknown"


def rebuild_venv():
    """Rebuild the venv with current Python."""
    log(f"🔄 Rebuilding venv...")

    # Remove old venv
    subprocess.run(["rm", "-rf", str(VENV_PATH)], check=True)
    log(f"  ✓ Removed old venv")

    # Create new venv
    subprocess.run(["/usr/bin/env", "python3", "-m", "venv", str(VENV_PATH)],
                   check=True, capture_output=True)
    log(f"  ✓ Created new venv")

    # Install requirements if requirements.txt exists
    req_file = REPO_ROOT / "requirements.txt"
    if req_file.exists():
        subprocess.run([str(VENV_PATH / "bin" / "pip"), "install",
                       "-q", "-r", str(req_file)],
                       check=True, capture_output=True)
        log(f"  ✓ Installed requirements")
    else:
        # Fallback: install common packages for RTO tracker
        packages = ["click", "pyobjc-core", "pyobjc-framework-CoreWLAN",
                   "google-auth-oauthlib", "google-auth-httplib2", "google-api-python-client"]
        subprocess.run([str(VENV_PATH / "bin" / "pip"), "install",
                       "-q"] + packages,
                       check=True, capture_output=True)
        log(f"  ✓ Installed packages")

    log(f"✅ venv rebuild complete")


def main():
    """Check venv health and rebuild if needed."""
    os.makedirs(LOG_FILE.parent, exist_ok=True)

    system_version = get_system_python_version()
    venv_version = get_venv_python_version()

    log(f"📊 Health check: system={system_version}, venv={venv_version}")

    # Extract version numbers for comparison (e.g., "3.14.8" from "Python 3.14.8")
    def extract_version(version_str: str) -> str:
        return version_str.split()[-1] if " " in version_str else version_str

    system_ver = extract_version(system_version)
    venv_ver = extract_version(venv_version)

    if system_ver != venv_ver and venv_version != "venv not found":
        log(f"⚠️  Version mismatch detected!")
        try:
            rebuild_venv()
        except Exception as e:
            log(f"❌ Rebuild failed: {e}")
            sys.exit(1)
    else:
        log(f"✅ venv is healthy (no rebuild needed)")


if __name__ == "__main__":
    main()
