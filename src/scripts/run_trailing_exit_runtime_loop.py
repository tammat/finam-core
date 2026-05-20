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

        for step_name, script_name in (
            ("real_portfolio_position_sync", "src/scripts/run_real_portfolio_position_sync.py"),
            ("real_portfolio_price_sync", "src/scripts/run_real_portfolio_price_sync.py"),
            ("trailing_exit_state_supervisor", "src/scripts/run_trailing_exit_state_supervisor.py"),
        ):
            print(f"TRAILING_EXIT_LOOP_STEP_BEGIN name={step_name}", flush=True)

            result = subprocess.run([
                py,
                script_name,
            ])

            if result.returncode != 0:
                raise RuntimeError(
                    f"TRAILING_EXIT_LOOP_STEP_FAILED name={step_name} rc={result.returncode}"
                )

            print(f"TRAILING_EXIT_LOOP_STEP_OK name={step_name}", flush=True)

        if tick < max_ticks:
            time.sleep(interval_sec)

    print(f"TRAILING_EXIT_RUNTIME_LOOP_OK ticks={max_ticks}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
