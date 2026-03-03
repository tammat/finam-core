from dataclasses import dataclass


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reason: str | None = None

    @staticmethod
    def allow():
        return RiskDecision(True, None)

    @staticmethod
    def reject(reason: str):
        return RiskDecision(False, reason)