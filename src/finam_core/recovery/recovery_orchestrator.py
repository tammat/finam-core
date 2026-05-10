from __future__ import annotations

from dataclasses import dataclass

from finam_core.reconciliation.startup_recovery_gate import StartupRecoveryGate


@dataclass(frozen=True)
class RecoveryCheckResult:
    ok: bool
    reason: str


class RecoveryOrchestrator:
    """Русский комментарий: центральный recovery coordinator перед запуском pipeline."""

    def __init__(self, startup_gate: StartupRecoveryGate | None = None) -> None:
        self.startup_gate = startup_gate or StartupRecoveryGate()

    def run_checks(self) -> RecoveryCheckResult:
        decision = self.startup_gate.check()

        allowed = getattr(decision, "allowed", False)
        reason = getattr(decision, "reason", "unknown")

        if not allowed:
            return RecoveryCheckResult(
                ok=False,
                reason=f"startup_gate_failed:{reason}",
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
