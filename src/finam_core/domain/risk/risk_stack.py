from finam_core.domain.risk.rule import RiskRule
from finam_core.domain.risk.risk_decision import RiskDecision
from finam_core.domain.risk.risk_context import RiskContext


class RiskStack:

    def __init__(self, rules: list[RiskRule] | None = None):
        self.rules = rules or []
        self.frozen: bool = False
        self.freeze_reason: str | None = None

    
    def evaluate(self, context):

        if self.frozen:

            return RiskDecision.reject(self.freeze_reason or "frozen")


        for rule in self.rules:

            decision = rule.evaluate(context)


            # --- Compatibility normalization ---

            # Some legacy rules may return:

            #   - RiskDecision

            #   - bool

            #   - (bool, reason)

            # Normalize everything to RiskDecision.

            if isinstance(decision, tuple):

                allowed = bool(decision[0]) if len(decision) > 0 else False

                reason = decision[1] if len(decision) > 1 else None

                decision = RiskDecision.allow() if allowed else RiskDecision.reject(str(reason) if reason else "rejected")

            elif isinstance(decision, bool):

                decision = RiskDecision.allow() if decision else RiskDecision.reject("rejected")

            elif decision is None:

                # Treat None as allow (rule abstains)

                decision = RiskDecision.allow()


            if not getattr(decision, "allowed", False):

                return decision


        return RiskDecision.allow()


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