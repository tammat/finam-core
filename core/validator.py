from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, Set

from core.state import PortfolioState


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str


class StateValidator:
    def __init__(
        self,
        *,
        max_abs_cash: Decimal = Decimal("1000000000000"),
        max_abs_pnl: Decimal = Decimal("1000000000000"),
        allow_negative_cash: bool = True,
        strict_equity_reconcile: bool = True,
    ):
        self.max_abs_cash = max_abs_cash
        self.max_abs_pnl = max_abs_pnl
        self.allow_negative_cash = allow_negative_cash
        self.strict_equity_reconcile = strict_equity_reconcile

    def validate(self, state: PortfolioState) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        # A) cash sanity
        if state.cash.is_nan():
            issues.append(ValidationIssue("CASH_NAN", "cash is NaN"))
        if abs(state.cash) > self.max_abs_cash:
            issues.append(ValidationIssue("CASH_ABS_LIMIT", f"cash abs({state.cash}) exceeds limit"))
        if (not self.allow_negative_cash) and state.cash < 0:
            issues.append(ValidationIssue("CASH_NEGATIVE", f"cash is negative: {state.cash}"))

        # B) pnl sanity
        for name, val in [("realized_pnl", state.realized_pnl), ("fees", state.fees)]:
            if val.is_nan():
                issues.append(ValidationIssue("PNL_NAN", f"{name} is NaN"))
            if abs(val) > self.max_abs_pnl:
                issues.append(ValidationIssue("PNL_ABS_LIMIT", f"{name} abs({val}) exceeds limit"))

        # C) positions canonical form
        seen: Set[str] = set()
        for sym, pos in state.positions.items():
            if sym in seen:
                issues.append(ValidationIssue("POS_DUP", f"duplicate symbol in positions: {sym}"))
            seen.add(sym)

            if sym != pos.symbol:
                issues.append(ValidationIssue("POS_KEY_MISMATCH", f"key {sym} != pos.symbol {pos.symbol}"))

            if pos.avg_price < 0:
                issues.append(ValidationIssue("POS_AVGPRICE_NEG", f"{sym}: avg_price < 0"))

            if pos.qty == 0:
                issues.append(ValidationIssue("POS_FLAT_STORED", f"{sym}: qty==0 but stored"))

            if pos.qty == 0 and pos.unrealized_pnl != 0:
                issues.append(ValidationIssue("POS_FLAT_UPNL", f"{sym}: qty==0 but unrealized_pnl={pos.unrealized_pnl}"))

        # D) equity reconcile (если задано)
        calc_eq = state.calc_equity()
        if state.equity is not None and self.strict_equity_reconcile and state.equity != calc_eq:
            issues.append(ValidationIssue("EQUITY_MISMATCH", f"equity={state.equity} != cash+unrealized={calc_eq}"))

        # E) fees sign (стоимость обычно <= 0)
        if state.fees > 0:
            issues.append(ValidationIssue("FEES_SIGN", f"fees expected <= 0, got {state.fees}"))

        return issues

    def assert_valid(self, state: PortfolioState, context: Optional[str] = None) -> None:
        issues = self.validate(state)
        if issues:
            prefix = f"[StateValidator] {context}: " if context else "[StateValidator] "
            msg = prefix + "; ".join(f"{i.code}: {i.message}" for i in issues)
            raise RuntimeError(msg)