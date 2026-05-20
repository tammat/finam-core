from __future__ import annotations

import os
import subprocess
import sys


def run_step(name: str, cmd: list[str]) -> None:
    print(f"STARTUP_RECOVERY_STEP_BEGIN name={name}", flush=True)

    result = subprocess.run(cmd)

    if result.returncode != 0:
        raise RuntimeError(
            f"STARTUP_RECOVERY_STEP_FAILED name={name} rc={result.returncode}"
        )

    print(f"STARTUP_RECOVERY_STEP_OK name={name}", flush=True)


def main() -> int:
    python = sys.executable

    env = os.environ.copy()

    run_step(
        "sending_intent_recovery",
        [
            python,
            "src/scripts/run_sending_intent_recovery.py",
        ],
    )

    run_step(
        "real_order_state_sync",
        [
            python,
            "src/scripts/run_real_order_state_synchronizer.py",
        ],
    )

    print("STARTUP_EXECUTION_RECOVERY_CHAIN_OK", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
