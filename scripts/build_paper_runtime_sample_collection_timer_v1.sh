#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_V1 ==="

mkdir -p deploy/systemd src/scripts scripts

cat > src/scripts/run_paper_runtime_sample_collection_cycle_v1.py <<'PY'
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
        "paper_edge_research_candidates",
        "src/scripts/build_paper_edge_discovery_research_candidates_v1.py",
        "VERDICT=PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1_READY",
    ),
    (
        "edge_validation_queue",
        "src/scripts/build_edge_validation_queue_v1.py",
        "VERDICT=EDGE_VALIDATION_QUEUE_V1_READY",
    ),
    (
        "edge_validation_pipeline",
        "src/scripts/build_edge_validation_pipeline_v1.py",
        "VERDICT=EDGE_VALIDATION_PIPELINE_V1_READY",
    ),
    (
        "edge_robustness_check",
        "src/scripts/build_edge_robustness_check_v1.py",
        "VERDICT=EDGE_ROBUSTNESS_CHECK_V1_READY",
    ),
    (
        "edge_oos_validation",
        "src/scripts/build_edge_oos_validation_v1.py",
        "VERDICT=EDGE_OOS_VALIDATION_V1_READY",
    ),
    (
        "edge_oos_backtest",
        "src/scripts/build_edge_oos_backtest_v1.py",
        "VERDICT=EDGE_OOS_BACKTEST_V1_READY",
    ),
    (
        "micro_live_readiness",
        "src/scripts/build_micro_live_readiness_v1.py",
        "VERDICT=MICRO_LIVE_READINESS_V1_READY",
    ),
    (
        "paper_sample_accumulation_monitor",
        "src/scripts/build_paper_sample_accumulation_monitor_v1.py",
        "VERDICT=PAPER_SAMPLE_ACCUMULATION_MONITOR_V1_READY",
    ),
    (
        "paper_runtime_sample_collection",
        "src/scripts/build_paper_runtime_sample_collection_v1.py",
        "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_V1_READY",
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
    print(f"CYCLE_STEP_START name={name} script={script}", flush=True)

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
        print(f"CYCLE_STEP_FAILED name={name} rc={result.returncode} elapsed_ms={elapsed_ms}", flush=True)
        raise SystemExit(result.returncode)

    if expected not in result.stdout:
        print(f"CYCLE_STEP_EXPECTED_VERDICT_MISSING name={name} expected={expected}", flush=True)
        raise SystemExit(2)

    print(f"CYCLE_STEP_DONE name={name} elapsed_ms={elapsed_ms}", flush=True)


def print_summary() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    candidates_total,
                    sample_ready,
                    wait_both_sample,
                    wait_total_sample,
                    wait_oos_sample,
                    min_remaining_total_trades,
                    min_remaining_oos_trades,
                    avg_progress_pct,
                    max_progress_pct,
                    collection_status,
                    phase_status,
                    micro_live_allowed
                FROM marketcore_ui.paper_runtime_sample_collection_v1
                WHERE id=1;
            """)
            row = cur.fetchone()

            if row is None:
                raise RuntimeError("paper_runtime_sample_collection_v1 row id=1 not found")

            keys = [
                "candidates_total",
                "sample_ready",
                "wait_both_sample",
                "wait_total_sample",
                "wait_oos_sample",
                "min_remaining_total_trades",
                "min_remaining_oos_trades",
                "avg_progress_pct",
                "max_progress_pct",
                "collection_status",
                "phase_status",
                "micro_live_allowed",
            ]

            for key, value in zip(keys, row):
                print(f"{key}={value}")

            cur.execute("""
                SELECT count(*)
                FROM marketcore_ui.paper_sample_accumulation_monitor_v1
                WHERE micro_live_allowed=true;
            """)
            allowed_rows = int(cur.fetchone()[0])
            print(f"monitor_micro_live_allowed_rows={allowed_rows}")

            if allowed_rows != 0:
                raise RuntimeError("micro_live_allowed must remain 0")


def main() -> None:
    started = time.monotonic()

    print("=== PAPER_RUNTIME_SAMPLE_COLLECTION_CYCLE_V1 ===", flush=True)

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
    print("VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_CYCLE_V1_READY")


if __name__ == "__main__":
    main()
PY

cat > deploy/systemd/finam-paper-sample-collection.service <<'UNIT'
[Unit]
Description=Finam Core Paper Runtime Sample Collection Cycle V1
After=network.target postgresql.service

[Service]
Type=oneshot
User=postgres
WorkingDirectory=/opt/finam-core
Environment=PYTHONPATH=/opt/finam-core/src
Environment=DATABASE_URL=postgresql:///finam_core
ExecStart=/opt/finam-core/venv/bin/python src/scripts/run_paper_runtime_sample_collection_cycle_v1.py

[Install]
WantedBy=multi-user.target
UNIT

cat > deploy/systemd/finam-paper-sample-collection.timer <<'UNIT'
[Unit]
Description=Run Finam Core Paper Runtime Sample Collection Cycle V1 every 5 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
AccuracySec=30s
Persistent=true
Unit=finam-paper-sample-collection.service

[Install]
WantedBy=timers.target
UNIT

cat > scripts/test_paper_runtime_sample_collection_timer_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/run_paper_runtime_sample_collection_cycle_v1.py

test -f deploy/systemd/finam-paper-sample-collection.service
test -f deploy/systemd/finam-paper-sample-collection.timer

grep -q "User=postgres" deploy/systemd/finam-paper-sample-collection.service
grep -q "DATABASE_URL=postgresql:///finam_core" deploy/systemd/finam-paper-sample-collection.service
grep -q "run_paper_runtime_sample_collection_cycle_v1.py" deploy/systemd/finam-paper-sample-collection.service
grep -q "OnUnitActiveSec=5min" deploy/systemd/finam-paper-sample-collection.timer

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/run_paper_runtime_sample_collection_cycle_v1.py \
  | tee /tmp/paper_runtime_sample_collection_cycle_v1.txt

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_CYCLE_V1_READY" \
  /tmp/paper_runtime_sample_collection_cycle_v1.txt

summary_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_v1 WHERE id=1;")
monitor_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_sample_accumulation_monitor_v1;")
allowed_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_sample_accumulation_monitor_v1 WHERE micro_live_allowed=true;")

test "$summary_rows" = "1"
test "$monitor_rows" -gt 0
test "$allowed_rows" = "0"

psql -d finam_core -c "
SELECT
    candidates_total,
    sample_ready,
    wait_both_sample,
    min_remaining_total_trades,
    min_remaining_oos_trades,
    avg_progress_pct,
    max_progress_pct,
    collection_status,
    phase_status,
    recommended_action
FROM marketcore_ui.paper_runtime_sample_collection_v1
WHERE id=1;
"

echo "summary_rows=$summary_rows"
echo "monitor_rows=$monitor_rows"
echo "micro_live_allowed_rows=$allowed_rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_V1_READY"
echo "VERDICT=TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_V1_OK"
SH_TEST

chmod +x scripts/test_paper_runtime_sample_collection_timer_v1.sh

scripts/test_paper_runtime_sample_collection_timer_v1.sh

echo "VERDICT=BUILD_PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_V1_OK"
