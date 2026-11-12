"""Memora quick runner.

Usage:
    python run.py backend     # Run FastAPI backend on http://127.0.0.1:8000
    python run.py frontend    # Run React frontend on http://127.0.0.1:5173
    python run.py tests       # Run backend pytest test suite
    python run.py             # Start both backend and frontend
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
VENV_PYTHON = VENV_DIR / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python")


def ensure_venv():
    """Ensure running inside .venv so dependencies are found."""
    if VENV_PYTHON.exists():
        current_exe = Path(sys.executable).resolve()
        target_exe = VENV_PYTHON.resolve()
        if current_exe != target_exe:
            # Re-execute with venv python
            args = [str(target_exe)] + sys.argv
            sys.exit(subprocess.call(args))


def run_backend():
    import uvicorn

    print("Starting Memora Backend on http://127.0.0.1:8000 ...")
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)


def run_frontend():
    print("Starting Memora Frontend on http://127.0.0.1:5173 ...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    subprocess.run([npm_cmd, "--prefix", "frontend", "run", "dev", "--", "--host", "127.0.0.1"])


def run_tests():
    import pytest

    sys.exit(pytest.main([]))


def run_all():
    ensure_venv()
    import uvicorn

    backend_cmd = [str(VENV_PYTHON), "-m", "uvicorn", "backend.main:app", "--port", "8000"]
    backend_proc = subprocess.Popen(backend_cmd)
    print("Started backend on http://127.0.0.1:8000 (PID: {})".format(backend_proc.pid))

    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    try:
        print("Starting frontend on http://127.0.0.1:5173 ...")
        subprocess.run([npm_cmd, "--prefix", "frontend", "run", "dev", "--", "--host", "127.0.0.1"])
    finally:
        print("Stopping backend...")
        backend_proc.terminate()
        try:
            backend_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend_proc.kill()


if __name__ == "__main__":
    ensure_venv()
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "all"

    if cmd == "backend":
        run_backend()
    elif cmd == "frontend":
        run_frontend()
    elif cmd in ("test", "tests"):
        run_tests()
    elif cmd in ("all", "dev"):
        run_all()
    else:
        print(f"Unknown command: {cmd}")
        print("Available options: backend, frontend, tests, all")
        sys.exit(1)

