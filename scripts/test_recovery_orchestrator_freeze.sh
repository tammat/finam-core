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


class FakeStartupGateBad:
    def check(self):
        return FakeDecision(allowed=False, reason="startup_recovery_freeze")


class FakeKillSwitch:
    def __init__(self):
        self.calls = []

    def activate(self, *, scope, reason, source):
        self.calls.append({
            "scope": scope,
            "reason": reason,
            "source": source,
        })


ks_bad = FakeKillSwitch()

result = RecoveryOrchestrator(
    startup_gate=FakeStartupGateBad(),
    kill_switch=ks_bad,
    freeze_on_failure=True,
).run_checks()

assert result.ok is False, result
assert result.reason == "recovery_orchestrator_failed:startup_recovery_freeze", result

assert len(ks_bad.calls) == 1, ks_bad.calls
assert ks_bad.calls[0]["scope"] == "GLOBAL", ks_bad.calls
assert ks_bad.calls[0]["reason"] == "recovery_orchestrator_failed:startup_recovery_freeze", ks_bad.calls
assert ks_bad.calls[0]["source"] == "recovery_orchestrator", ks_bad.calls

print("RECOVERY_ORCHESTRATOR_FREEZE_OK")
PY
