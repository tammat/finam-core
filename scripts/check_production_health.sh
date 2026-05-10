#!/usr/bin/env bash
set -euo pipefail

export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"
export PYTHON_BIN="${PYTHON_BIN:-/opt/finam-core/.venv/bin/python}"

FAIL=0

echo "[PROD] PostgreSQL"
"${PYTHON_BIN}" - <<'PY' || FAIL=1
import os
import psycopg2
conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.close()
print("POSTGRES_OK")
PY

echo "[PROD] Projection lag"
bash scripts/check_projection_lag.sh projection_worker 100 || FAIL=1

echo "[PROD] Recovery orchestrator"
bash scripts/check_recovery_orchestrator.sh || FAIL=1

echo "[PROD] DLQ"
bash scripts/check_dlq_health.sh fail || FAIL=1

echo "[PROD] Kill switch"
"${PYTHON_BIN}" - <<'PY' || FAIL=1
from finam_core.risk.persistent_kill_switch import PersistentKillSwitch

ks = PersistentKillSwitch()
state = ks.get_state()

print(f"KILL_SWITCH_STATE active={state.active} reason={state.reason}")

if state.active:
    raise SystemExit(1)
PY

if [ "$FAIL" -ne 0 ]; then
  echo "PRODUCTION_HEALTH_FAIL"
  exit 1
fi

echo "PRODUCTION_HEALTH_OK"
