from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finam_core.reconciliation.startup_recovery_gate import StartupRecoveryGate
from finam_core.risk.persistent_kill_switch import PersistentKillSwitch


@dataclass(frozen=True)
class RecoveryCheckResult:
    ok: bool
    reason: str


class RecoveryOrchestrator:
    """Русский комментарий: recovery coordinator с persistent freeze через kill switch."""

    def __init__(
        self,
        *,
        startup_gate: Any | None = None,
        kill_switch: Any | None = None,
        freeze_on_failure: bool = True,
    ) -> None:
        self.startup_gate = startup_gate or StartupRecoveryGate()
        self.kill_switch = kill_switch or PersistentKillSwitch()
        self.freeze_on_failure = bool(freeze_on_failure)

    def run_checks(self) -> RecoveryCheckResult:
        decision = self.startup_gate.check()

        allowed = bool(getattr(decision, "allowed", False))
        reason = str(getattr(decision, "reason", "unknown"))

        if not allowed:
            freeze_reason = f"recovery_orchestrator_failed:{reason}"

            if self.freeze_on_failure:
                self.kill_switch.activate(
                    scope="GLOBAL",
                    reason=freeze_reason,
                    source="recovery_orchestrator",
                )

            return RecoveryCheckResult(
                ok=False,
                reason=freeze_reason,
            )

        return RecoveryCheckResult(
            ok=True,
            reason="recovery_checks_passed",
        )


def main() -> None:
    result = RecoveryOrchestrator().run_checks()

    if result.ok:
        print(f"RECOVERY_ORCHESTRATOR_OK reason={result.reason}", flush=True)
        return

    print(f"RECOVERY_ORCHESTRATOR_FAIL reason={result.reason}", flush=True)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
