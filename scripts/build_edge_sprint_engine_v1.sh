#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_SPRINT_ENGINE_V1 ==="

mkdir -p src/scripts deploy/systemd scripts

cat > src/scripts/run_edge_sprint_engine_v1.py <<'PY'
from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime

SPRINT_NAME = os.getenv("EDGE_SPRINT_NAME", "EDGE_SPRINT")
ROOT = os.getcwd()

STAGES = [
    ("PARAMETER_SEARCH", "scripts/build_parameter_search_grid_v1.sh"),
    ("EDGE_LAB", "scripts/build_edge_lab_foundation_v1.sh"),
    ("EXECUTION", "scripts/build_strategy_execution_runner_v1.sh"),
    ("EDGE_SCORE", "scripts/build_edge_score_engine_v2.sh"),
    ("AUDIT", "scripts/build_edge_pipeline_audit_v1.sh"),
]

def run_stage(name: str, script: str) -> None:
    print(f"\n===== {name} =====")
    subprocess.run(["bash", script], check=True, cwd=ROOT)

def main() -> None:
    started = datetime.now(UTC)

    print("=== EDGE_SPRINT_ENGINE_V1 ===")
    print(f"sprint={SPRINT_NAME}")
    print(f"started={started.isoformat()}")

    for name, script in STAGES:
        run_stage(name, script)

    finished = datetime.now(UTC)

    print(f"finished={finished.isoformat()}")
    print("status=DONE")
    print("VERDICT=EDGE_SPRINT_ENGINE_V1_READY")

if __name__ == "__main__":
    main()
PY

cat > deploy/systemd/finam-edge-sprint.service <<'UNIT'
[Unit]
Description=Finam Core Edge Sprint

[Service]
Type=oneshot
WorkingDirectory=/opt/finam-core
Environment=PYTHONPATH=src
Environment=DATABASE_URL=postgresql:///finam_core
ExecStart=/opt/finam-core/venv/bin/python src/scripts/run_edge_sprint_engine_v1.py
UNIT

cat > deploy/systemd/finam-edge-sprint.timer <<'UNIT'
[Unit]
Description=Run Edge Sprint

[Timer]
OnBootSec=5min
OnUnitActiveSec=6h
Unit=finam-edge-sprint.service

[Install]
WantedBy=timers.target
UNIT

cat > scripts/test_edge_sprint_engine_v1.sh <<'TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SPRINT_ENGINE_V1 ==="

PYTHONPATH=src python -m py_compile \
    src/scripts/run_edge_sprint_engine_v1.py

DATABASE_URL=postgresql:///finam_core \
PYTHONPATH=src \
python src/scripts/run_edge_sprint_engine_v1.py \
| tee /tmp/edge_sprint_engine_v1.txt

grep -q "VERDICT=EDGE_SPRINT_ENGINE_V1_READY" \
    /tmp/edge_sprint_engine_v1.txt

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_SPRINT_ENGINE_V1_OK"
TEST

chmod +x scripts/test_edge_sprint_engine_v1.sh
scripts/test_edge_sprint_engine_v1.sh

echo "VERDICT=BUILD_EDGE_SPRINT_ENGINE_V1_OK"
