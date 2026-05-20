from __future__ import annotations

import os
import subprocess
import sys
import time


def main() -> int:
    interval_sec = int(os.getenv("TRAILING_EXIT_LOOP_INTERVAL_SEC", "15"))
    max_ticks = int(os.getenv("TRAILING_EXIT_LOOP_MAX_TICKS", "1"))

    py = sys.executable

    for tick in range(1, max_ticks + 1):
        print(f"TRAILING_EXIT_LOOP_TICK tick={tick}", flush=True)

        result = subprocess.run([
            py,
            "src/scripts/run_trailing_exit_state_supervisor.py",
        ])

        if result.returncode != 0:
            raise RuntimeError(f"TRAILING_EXIT_LOOP_STEP_FAILED rc={result.returncode}")

        if tick < max_ticks:
            time.sleep(interval_sec)

    print(f"TRAILING_EXIT_RUNTIME_LOOP_OK ticks={max_ticks}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
