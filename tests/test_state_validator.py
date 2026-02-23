from decimal import Decimal

from core.state import PortfolioState, Position
from core.validator import StateValidator


def _must_fail(fn, contains: str) -> None:
    try:
        fn()
    except RuntimeError as e:
        if contains not in str(e):
            raise SystemExit(f"expected error containing {contains!r}, got: {e}")
        return
    raise SystemExit("expected failure, but it passed")


def main() -> int:
    v = StateValidator(allow_negative_cash=True, strict_equity_reconcile=True)

    # OK
    s = PortfolioState(cash=Decimal("1000"), fees=Decimal("-1.5"), equity=Decimal("1100"))
    s.upsert_position(Position(symbol="BRH6", qty=Decimal("1"), avg_price=Decimal("70"), unrealized_pnl=Decimal("100")))
    v.assert_valid(s, context="ok")

    # BAD: equity mismatch
    def case_equity_mismatch():
        bad = PortfolioState(cash=Decimal("1000"), fees=Decimal("0"), equity=Decimal("999"))
        bad.upsert_position(Position(symbol="NGG6", qty=Decimal("1"), avg_price=Decimal("3"), unrealized_pnl=Decimal("0")))
        v.assert_valid(bad, context="equity_mismatch")
    _must_fail(case_equity_mismatch, "EQUITY_MISMATCH")

    # BAD: flat stored
    def case_flat_stored():
        bad = PortfolioState(cash=Decimal("0"), fees=Decimal("0"), equity=Decimal("0"))
        bad.upsert_position(Position(symbol="SBER", qty=Decimal("0"), avg_price=Decimal("250"), unrealized_pnl=Decimal("0")))
        v.assert_valid(bad, context="flat_stored")
    _must_fail(case_flat_stored, "POS_FLAT_STORED")

    # BAD: fees sign
    def case_fees_sign():
        bad = PortfolioState(cash=Decimal("0"), fees=Decimal("1"), equity=Decimal("0"))
        v.assert_valid(bad, context="fees_sign")
    _must_fail(case_fees_sign, "FEES_SIGN")

    print("ok: StateValidator tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())