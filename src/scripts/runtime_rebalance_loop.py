from __future__ import annotations

import os
import subprocess


def run(cmd: list[str]) -> None:
    print("RUNTIME_REBALANCE_RUN " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main() -> int:
    python_bin = os.getenv("PYTHON_BIN", "python")
    env = os.environ.copy()
    env["PYTHONPATH"] = env.get("PYTHONPATH", "src")

    steps = [
        [python_bin, "src/scripts/update_market_opportunity_metrics.py"],
        [python_bin, "src/scripts/update_dynamic_watchlist_from_opportunities.py"],
    ]

    for cmd in steps:
        subprocess.run(cmd, env=env, check=True)

    print("OK: runtime rebalance loop completed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
