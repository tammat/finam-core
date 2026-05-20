from __future__ import annotations

import subprocess
import sys


def run(name: str, cmd: list[str]) -> None:
    print(f"RUNTIME_RECOVERY_STEP_BEGIN name={name}", flush=True)
    result = subprocess.run(cmd)

    if result.returncode != 0:
        raise RuntimeError(f"RUNTIME_RECOVERY_STEP_FAILED name={name} rc={result.returncode}")

    print(f"RUNTIME_RECOVERY_STEP_OK name={name}", flush=True)


def main() -> int:
    py = sys.executable

    run("sending_intent_recovery", [py, "src/scripts/run_sending_intent_recovery.py"])
    run("client_order_id_recovery_lookup", [py, "src/scripts/run_client_order_id_recovery_lookup.py"])
    run("real_order_state_synchronizer", [py, "src/scripts/run_real_order_state_synchronizer.py"])
    run("oms_invariant_audit", [py, "src/scripts/run_oms_invariant_audit.py"])
    run("execution_correctness_audit", [py, "src/scripts/run_execution_correctness_audit.py"])

    print("RUNTIME_RECOVERY_INTEGRATION_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
