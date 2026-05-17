from __future__ import annotations

import os
import signal
import subprocess
import sys


class RuntimeSubprocessWorker:
    """Русский комментарий: subprocess-worker для запуска paper_pipeline по одному symbol."""

    def __init__(self, symbol: str, *, run_secs: int = 60) -> None:
        self.symbol = symbol
        self.run_secs = run_secs
        self.process: subprocess.Popen | None = None

    def start(self) -> "RuntimeSubprocessWorker":
        env = os.environ.copy()
        env["PYTHONPATH"] = env.get("PYTHONPATH", "src")
        env.setdefault("EXECUTION_MODE", "paper")
        env.setdefault("ENABLE_RUNTIME_ACTIVE_UNIVERSE_GATE", "1")

        cmd = [
            sys.executable,
            "src/scripts/run_market_pipeline.py",
            "--symbol",
            self.symbol,
            "--run-secs",
            str(self.run_secs),
        ]

        print(f"RUNTIME_SUBPROCESS_WORKER_START symbol={self.symbol}", flush=True)
        self.process = subprocess.Popen(cmd, env=env)
        return self

    def stop(self) -> None:
        if self.process is None:
            return

        if self.process.poll() is not None:
            return

        print(f"RUNTIME_SUBPROCESS_WORKER_STOP symbol={self.symbol}", flush=True)
        self.process.send_signal(signal.SIGTERM)

        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            print(f"RUNTIME_SUBPROCESS_WORKER_KILL symbol={self.symbol}", flush=True)
            self.process.kill()
