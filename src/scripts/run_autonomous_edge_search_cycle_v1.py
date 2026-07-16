from __future__ import annotations

import os
import subprocess
from pathlib import Path

import psycopg2


ROOT = Path("/opt/finam-core")
PYTHON = ROOT / "venv/bin/python"
LOCK_ID = 741903126
STEPS = (
    "src/scripts/build_edge_regime_hypothesis_discovery_v2.py",
    "src/scripts/build_walkforward_edge_search_v3.py",
    "src/scripts/promote_regime_oos_to_canonical_v1.py",
    "src/scripts/build_profit_funnel_validated_edge_v2.py",
    "src/scripts/build_profit_funnel_oos_forward_handoff_v2.py",
    "src/scripts/admit_oos_forward_clean_cohort_v1.py",
    "src/scripts/run_forward_edge_observation_worker_v1.py",
    "src/scripts/project_forward_edge_shadow_trades_v1.py",
    "src/scripts/build_profit_funnel_shadow_paper_admission_v2.py",
    "src/scripts/build_profit_funnel_transition_lineage_v2.py",
)


def main() -> int:
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(ROOT / "src"),
        "DATABASE_URL": "postgresql:///finam_core",
        "RUNTIME_ALLOW_TRADING": "0",
        "EXECUTION_ENABLED": "0",
        "REAL_TRADING_ENABLED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    with psycopg2.connect("postgresql:///finam_core") as lock_connection:
        with lock_connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_ID,))
            if not cursor.fetchone()[0]:
                print("cycle_skipped=1")
                print("reason=AUTONOMOUS_EDGE_SEARCH_ALREADY_RUNNING")
                return 0
        for step in STEPS:
            result = subprocess.run(
                (str(PYTHON), step), cwd=ROOT, env=env,
                text=True, capture_output=True, timeout=1800, check=False,
            )
            print(f"step={step}|returncode={result.returncode}")
            if result.stdout:
                print(result.stdout.rstrip())
            if result.returncode != 0:
                if result.stderr:
                    print(result.stderr.rstrip())
                print("VERDICT=AUTONOMOUS_EDGE_SEARCH_CYCLE_FAILED")
                return 2
    print("paper_promotion_changed=0")
    print("runtime_changed=0")
    print("live_allowed=0")
    print("VERDICT=AUTONOMOUS_EDGE_SEARCH_CYCLE_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
