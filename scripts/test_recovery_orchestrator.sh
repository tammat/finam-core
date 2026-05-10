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


class FakeStartupGateBad:
    def check(self):
        return FakeDecision(allowed=False, reason="startup_recovery_freeze")


ok = RecoveryOrchestrator(startup_gate=FakeStartupGateOk()).run_checks()
assert ok.ok is True, ok
assert ok.reason == "recovery_checks_passed", ok

bad = RecoveryOrchestrator(startup_gate=FakeStartupGateBad()).run_checks()
assert bad.ok is False, bad
assert bad.reason == "startup_gate_failed:startup_recovery_freeze", bad

print("RECOVERY_ORCHESTRATOR_TEST_OK")
PY
