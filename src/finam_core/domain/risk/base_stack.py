from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class RiskStackBundle:
    """Bundle for pre-trade and post-trade risk stacks with snapshot-able state."""
    pre_trade: Any
    post_trade: Any

    def __init__(self, pre_trade, post_trade):
        self.pre_trade = pre_trade
        self.post_trade = post_trade

        # ← ДОБАВИТЬ
        self.frozen = False
        self.freeze_reason = None
    def get_state(self) -> Dict[str, Any]:
        state: Dict[str, Any] = {}
        if hasattr(self.pre_trade, "get_state"):
            state["pre_trade"] = self.pre_trade.get_state()
        if hasattr(self.post_trade, "get_state"):
            state["post_trade"] = self.post_trade.get_state()
        return state

    def load_state(self, state: Dict[str, Any]) -> None:
        if not state:
            return
        if hasattr(self.pre_trade, "load_state") and "pre_trade" in state:
            self.pre_trade.load_state(state["pre_trade"])
        if hasattr(self.post_trade, "load_state") and "post_trade" in state:
            self.post_trade.load_state(state["post_trade"])

    def to_dict(self):
        return {
            "frozen": self.frozen,
            "freeze_reason": self.freeze_reason,
        }