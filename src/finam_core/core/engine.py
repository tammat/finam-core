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
# risk/risk_engine.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional


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
# -------------------- Structured Decision -------------------
# ============================================================

@dataclass(frozen=True)
class RiskDecision:
    """Structured decision that remains stable for logging / storage.

    Public contract: RiskEngine.evaluate(intent, context) still returns an object
    with .allowed/.reason/.freeze fields (RiskResult). RiskDecision is attached
    for downstream auditability without forcing call-site changes.
    """

    allowed: bool
    reason: Optional[str] = None
    freeze: bool = False
    rule: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


# ============================================================
# ---------------------- Risk Result -------------------------
# ============================================================

@dataclass
class RiskResult:
    """Backward-compatible result object.

    Existing code expects: allowed/reason/freeze.
    We add: decision (structured payload).
    """

    allowed: bool
    reason: Optional[str] = None
    freeze: bool = False
    decision: Optional[RiskDecision] = None


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

    def _attach(self, result: RiskResult, rule_name: Optional[str]) -> RiskResult:
        """Ensure result.decision is always present."""
        if result.decision is None:
            result.decision = RiskDecision(
                allowed=result.allowed,
                reason=result.reason,
                freeze=result.freeze,
                rule=rule_name,
            )
        return result

    def evaluate(self, intent, context: RiskContext) -> RiskResult:
        """Deterministic rule evaluation.

        Contract preserved:
          - signature unchanged
          - return type still has allowed/reason/freeze
        """

        if self._frozen:
            return RiskResult(
                False,
                "GLOBAL_FREEZE",
                freeze=True,
                decision=RiskDecision(False, "GLOBAL_FREEZE", freeze=True, rule="RiskEngine"),
            )

        for rule in self.rules:
            result = rule.evaluate(intent, context)
            result = self._attach(result, rule.__class__.__name__)

            if not result.allowed:
                if result.freeze:
                    self._frozen = True
                return result

        return RiskResult(True, decision=RiskDecision(True, rule="ALLOW"))


__all__ = [
    "RiskContext",
    "RiskDecision",
    "RiskResult",
    "BaseRiskRule",
    "RiskEngine",
]