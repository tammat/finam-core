#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

"${PYTHON_BIN:-/opt/finam-core/.venv/bin/python}" - <<'PY'
import sys

from finam_core.recovery.recovery_orchestrator import (
    RecoveryOrchestrator,
)

orchestrator = RecoveryOrchestrator()

result = orchestrator.run_checks()

if result.ok:
    print(
        "RECOVERY_ORCHESTRATOR_HEALTH_OK "
        f"reason={result.reason}"
    )
    sys.exit(0)

print(
    "RECOVERY_ORCHESTRATOR_HEALTH_FAIL "
    f"reason={result.reason}"
)

sys.exit(2)
PY
