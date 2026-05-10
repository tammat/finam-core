#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
from dataclasses import dataclass

from finam_core.recovery.recovery_orchestrator import RecoveryOrchestrator


@dataclass
class FakeDecision:
    allowed: bool
    reason: str


class FakeStartupGateOk:
    def check(self):
        return FakeDecision(allowed=True, reason="startup_recovery_ok")


result = RecoveryOrchestrator(
    startup_gate=FakeStartupGateOk(),
    freeze_on_failure=True,
).run_checks()

assert result.ok is True, result
assert result.reason == "recovery_checks_passed", result

print("RECOVERY_ORCHESTRATOR_TEST_OK")
PY
