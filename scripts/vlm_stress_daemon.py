#!/usr/bin/env python3
"""
Daemon launcher for the VLM stress test.

Forks into background, detaches from controlling terminal, and runs the
stress test to completion. Survives parent shell termination.
"""

import os
import sys
from pathlib import Path

SCRIPT_DIR = Path("/home/z/my-project/scripts")
LOG_PATH = SCRIPT_DIR / "vlm_stress_test_full.log"
PID_PATH = SCRIPT_DIR / "vlm_stress_test.pid"


def daemonize() -> None:
    """Standard double-fork daemonization."""
    # First fork
    if os.fork() > 0:
        return  # Parent exits

    # Decouple from parent environment
    os.setsid()

    # Second fork
    if os.fork() > 0:
        os._exit(0)

    # Redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()

    log_fd = os.open(str(LOG_PATH), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    null_fd = os.open(os.devnull, os.O_RDONLY)

    os.dup2(null_fd, 0)  # stdin
    os.dup2(log_fd, 1)   # stdout
    os.dup2(log_fd, 2)   # stderr

    os.close(null_fd)
    os.close(log_fd)

    # Write PID file
    PID_PATH.write_text(str(os.getpid()))


def main() -> None:
    daemonize()

    # If we're the parent, exit immediately
    if not PID_PATH.exists() or os.getppid() == 1:
        # We're the daemon child — run the stress test
        os.environ.setdefault("VLM_STRESS_NUM_CALLS", "100")
        os.environ.setdefault("VLM_STRESS_RUNS", "2")
        os.environ.setdefault("VLM_STRESS_INTER_CALL_DELAY", "1.5")

        # Add scripts dir to path and import
        sys.path.insert(0, str(SCRIPT_DIR))
        # Import after path setup
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "vlm_stress_test",
            str(SCRIPT_DIR / "vlm_stress_test.py"),
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Run the async main
        import asyncio
        asyncio.run(module.main())
    else:
        # Parent process — just print PID
        print(f"Daemon launched with PID: {PID_PATH.read_text().strip()}")


if __name__ == "__main__":
    main()
