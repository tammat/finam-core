from typing import List


class PostTradeRiskStack:
    def __init__(self, rules: List):
        self.rules = rules or []

    def evaluate(self, context):
        for rule in self.rules:
            decision = rule.evaluate(context)
            if not decision.allowed:
                return decision
        return type("Decision", (), {"allowed": True})()

    def get_state(self):
        state = {}
        for rule in self.rules:
            if hasattr(rule, "get_state"):
                state[rule.__class__.__name__] = rule.get_state()
        return state

    def load_state(self, state):
        if not state:
            return
        for rule in self.rules:
            if hasattr(rule, "load_state"):
                rule_state = state.get(rule.__class__.__name__)
                if rule_state:
                    rule.load_state(rule_state)