from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class RiskDecision:
    allowed: bool
    reason: str | None = None
    new_qty: float | None = None
    freeze: bool = False


class RiskStack:

    def __init__(self, rules: list, frozen: bool = False, freeze_reason: str | None = None):
        self.rules = rules
        self.frozen = frozen
        self.freeze_reason = freeze_reason
        self.freeze_ts: datetime | None = None

    def evaluate(self, intent, portfolio):

        if self.frozen:
            return RiskDecision(False, "system frozen")

        for rule in self.rules:
            decision = rule.evaluate(intent, portfolio)

            if decision.freeze:
                self.frozen = True
                self.freeze_reason = decision.reason
                self.freeze_ts = datetime.utcnow()
                return decision

            if not decision.allowed:
                return decision

            if decision.new_qty is not None:
                intent.qty = decision.new_qty

        return RiskDecision(True)

    # ---------- PERSISTENCE ----------

    def get_state(self):
        return {
            "frozen": self.frozen,
            "freeze_reason": self.freeze_reason,
            "freeze_ts": self.freeze_ts.isoformat() if self.freeze_ts else None,
        }

    def load_state(self, data: dict):
        self.frozen = data.get("frozen", False)
        self.freeze_reason = data.get("freeze_reason")
        ts = data.get("freeze_ts")
        if ts:
            from datetime import datetime
            self.freeze_ts = datetime.fromisoformat(ts)