from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import psycopg2


ROOT = Path(__file__).resolve().parents[2]
DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

STEPS = [
    (
        "timer_health",
        "src/scripts/build_paper_runtime_sample_collection_timer_health_v1.py",
        "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1_READY",
    ),
    (
        "phase_close",
        "src/scripts/build_paper_runtime_sample_collection_phase_close_v1.py",
        "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1_READY",
    ),
    (
        "phase_ii_summary",
        "src/scripts/build_phase_ii_paper_edge_discovery_summary_v1.py",
        "VERDICT=PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1_READY",
    ),
    (
        "operations",
        "src/scripts/build_paper_runtime_sample_collection_operations_v1.py",
        "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_V1_READY",
    ),
]


def run_step(name: str, script: str, expected: str) -> None:
    script_path = ROOT / script
    if not script_path.exists():
        raise FileNotFoundError(str(script_path))

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env.setdefault("DATABASE_URL", DB)

    started = time.monotonic()
    print(f"OPERATIONS_CYCLE_STEP_START name={name} script={script}", flush=True)

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
    )

    elapsed_ms = int((time.monotonic() - started) * 1000)

    if result.stdout:
        print(result.stdout, end="", flush=True)

    if result.stderr:
        print(result.stderr, end="", file=sys.stderr, flush=True)

    if result.returncode != 0:
        print(f"OPERATIONS_CYCLE_STEP_FAILED name={name} rc={result.returncode} elapsed_ms={elapsed_ms}", flush=True)
        raise SystemExit(result.returncode)

    if expected not in result.stdout:
        print(f"OPERATIONS_CYCLE_EXPECTED_VERDICT_MISSING name={name} expected={expected}", flush=True)
        raise SystemExit(2)

    print(f"OPERATIONS_CYCLE_STEP_DONE name={name} elapsed_ms={elapsed_ms}", flush=True)


def print_summary() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    count(*) AS rows,
                    count(*) FILTER (WHERE micro_live_allowed=true) AS allowed_rows,
                    count(*) FILTER (WHERE operation_priority='HIGH') AS high_rows,
                    count(*) FILTER (WHERE operation_status='NEAR_SAMPLE_READY') AS near_ready_rows,
                    count(*) FILTER (WHERE operation_status='COLLECTING') AS collecting_rows
                FROM marketcore_ui.paper_runtime_sample_collection_operations_v1;
            """)
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("operations summary not found")

            rows, allowed_rows, high_rows, near_ready_rows, collecting_rows = row

            print(f"operations_rows={rows}")
            print(f"operations_micro_live_allowed_rows={allowed_rows}")
            print(f"operations_high_rows={high_rows}")
            print(f"operations_near_ready_rows={near_ready_rows}")
            print(f"operations_collecting_rows={collecting_rows}")

            if int(allowed_rows or 0) != 0:
                raise RuntimeError("micro_live_allowed must remain 0")

            cur.execute("""
                SELECT
                    phase_result_status,
                    engineering_status,
                    operational_status,
                    timer_health_status,
                    next_phase
                FROM marketcore_ui.phase_ii_paper_edge_discovery_summary_v1
                WHERE id=1;
            """)
            phase = cur.fetchone()
            if phase:
                keys = [
                    "phase_result_status",
                    "engineering_status",
                    "operational_status",
                    "timer_health_status",
                    "next_phase",
                ]
                for key, value in zip(keys, phase):
                    print(f"{key}={value}")


def main() -> None:
    started = time.monotonic()

    print("=== PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_CYCLE_V1 ===", flush=True)

    for name, script, expected in STEPS:
        run_step(name, script, expected)

    print_summary()

    total_ms = int((time.monotonic() - started) * 1000)
    print(f"total_elapsed_ms={total_ms}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_CYCLE_V1_READY")


if __name__ == "__main__":
    main()
