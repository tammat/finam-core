from domain.risk.rule import RiskRule
from domain.risk.risk_decision import RiskDecision
from domain.risk.risk_context import RiskContext


class RiskStack:

    def __init__(self, rules: list[RiskRule] | None = None):
        self.rules = rules or []
        self.frozen: bool = False
        self.freeze_reason: str | None = None

    def evaluate(self, context: RiskContext) -> RiskDecision:
        if self.frozen:
            return RiskDecision.reject(self.freeze_reason or "frozen")

        for rule in self.rules:
            decision = rule.evaluate(context)
            if not decision.allowed:
                return decision

        return RiskDecision.allow()

    # ---- state persistence ----

    def get_state(self) -> dict:
        return {
            "frozen": self.frozen,
            "freeze_reason": self.freeze_reason,
            "rules": [
                rule.get_state() if hasattr(rule, "get_state") else None
                for rule in self.rules
            ],
        }

    def load_state(self, state: dict | None):
        if not state:
            return

        self.frozen = state.get("frozen", False)
        self.freeze_reason = state.get("freeze_reason")

        rule_states = state.get("rules", [])
        for rule, rule_state in zip(self.rules, rule_states):
            if hasattr(rule, "load_state"):
                rule.load_state(rule_state)