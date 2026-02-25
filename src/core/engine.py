# risk/risk_engine.py

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


# ============================================================
# ---------------------- Risk Context ------------------------
# ============================================================

@dataclass(frozen=True)
class RiskContext:
    equity: float
    daily_pnl: float
    drawdown_pct: float
    positions: dict
    exposure_by_asset: dict
    timestamp: datetime


# ============================================================
# ---------------------- Risk Result -------------------------
# ============================================================

@dataclass
class RiskResult:
    allowed: bool
    reason: Optional[str] = None
    freeze: bool = False


# ============================================================
# ---------------------- Base Rule ---------------------------
# ============================================================

class BaseRiskRule:
    def evaluate(self, intent, context: RiskContext) -> RiskResult:
        raise NotImplementedError


# ============================================================
# ---------------------- Risk Engine -------------------------
# ============================================================

class RiskEngine:

    def __init__(self, rules: Optional[List[BaseRiskRule]] = None):
        self.rules = rules or []
        self._frozen = False

    def is_frozen(self) -> bool:
        return self._frozen

    def reset_freeze(self) -> None:
        self._frozen = False

    def evaluate(self, intent, context: RiskContext) -> RiskResult:
        """
        Deterministic rule evaluation.
        First blocking rule stops evaluation.
        """

        if self._frozen:
            return RiskResult(False, "GLOBAL_FREEZE", freeze=True)

        for rule in self.rules:
            result = rule.evaluate(intent, context)

            if not result.allowed:
                if result.freeze:
                    self._frozen = True
                return result

        return RiskResult(True)