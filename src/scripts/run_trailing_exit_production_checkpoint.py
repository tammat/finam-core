from __future__ import annotations

import subprocess
import sys


def run(name: str, cmd: list[str]) -> None:
    print(f"TRAILING_CHECKPOINT_STEP_BEGIN name={name}", flush=True)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"TRAILING_CHECKPOINT_STEP_FAILED name={name} rc={result.returncode}")
    print(f"TRAILING_CHECKPOINT_STEP_OK name={name}", flush=True)


def main() -> int:
    py = sys.executable

    run("trailing_dry_run_audit", [py, "src/scripts/run_trailing_exit_dry_run_audit.py"])
    run("trailing_runtime_loop", [py, "src/scripts/run_trailing_exit_runtime_loop.py"])
    run("oms_invariant_audit", [py, "src/scripts/run_oms_invariant_audit.py"])
    run("execution_correctness_audit", [py, "src/scripts/run_execution_correctness_audit.py"])

    print("TRAILING_EXIT_PRODUCTION_CHECKPOINT_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
