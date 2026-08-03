from __future__ import annotations

import os
import subprocess
from pathlib import Path

import psycopg2


ROOT = Path("/opt/finam-core")
PYTHON = ROOT / "venv/bin/python"
DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
STEPS = (
    "src/scripts/analytics/build_entry_exit_optimizer_v1.py",
    "src/scripts/run_reachable_shadow_challenger_gate_v1.py",
    "src/scripts/check_reachable_shadow_morning_v1.py",
    "src/scripts/run_prospective_shadow_gate_v1.py",
    "src/scripts/maintain_entry_exit_oos_admissions_v1.py",
    "src/scripts/run_v5_purged_oos_worker_v1.py",
    "src/scripts/sync_direct_v5_promotion_workflow_v1.py",
    "src/scripts/run_adaptive_regime_pilot_v1.py",
)


def main() -> int:
    lock_connection = psycopg2.connect(DB)
    lock_connection.autocommit = True
    with lock_connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(184006)")
        if not cursor.fetchone()[0]:
            print("VERDICT=ENTRY_EXIT_CONTROL_CHAIN_ALREADY_RUNNING")
            return 0
    try:
        environment = dict(os.environ, PYTHONPATH="src", PYTHONDONTWRITEBYTECODE="1")
        for step in STEPS:
            print(f"ENTRY_EXIT_CONTROL_STEP={step}", flush=True)
            completed = subprocess.run([str(PYTHON), step], cwd=ROOT, env=environment, check=False)
            if completed.returncode:
                print(f"VERDICT=ENTRY_EXIT_CONTROL_CHAIN_FAILED step={step} rc={completed.returncode}")
                return completed.returncode
        print("VERDICT=ENTRY_EXIT_CONTROL_CHAIN_OK")
        return 0
    finally:
        with lock_connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(184006)")
        lock_connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
