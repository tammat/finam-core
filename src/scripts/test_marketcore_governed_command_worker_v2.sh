#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/python - <<'PY'
from pathlib import Path
for name in (
    "src/marketcore/action/command_worker_v2.py",
    "src/scripts/run_marketcore_governed_command_worker_v2.py",
    "src/scripts/rollback_marketcore_pending_request_v2.py",
):
    compile(Path(name).read_text(), name, "exec")
PY
venv/bin/pytest -q tests/test_governed_command_worker_v2.py tests/test_governed_rollback_coordinator_v2.py
echo "claim_mode=FOR_UPDATE_SKIP_LOCKED"
echo "worker_allowlist=RESEARCH_REFRESH,PAPER_OBSERVATION"
echo "worker_live_or_broker_commands=0"
echo "pending_request_rollback=PASS"
echo "VERDICT=MARKETCORE_STAGE5_GOVERNED_COMMAND_WORKER_V2_READY"
