import pytest

from finam_core.analytics.pnl_units import PnlUnitSpec, gross_pnl_rub, risk_rub


def test_futures_pnl_uses_tick_value_over_tick_size():
    spec = PnlUnitSpec("BRQ6@RTSX", "FUTURES", 10.0 / 0.01)
    assert gross_pnl_rub(side="LONG", entry_price=90, exit_price=90.05, qty=2, spec=spec) == pytest.approx(100)


def test_short_and_risk_use_same_cash_multiplier():
    spec = PnlUnitSpec("SBER@MISX", "EQUITY", 10)
    assert gross_pnl_rub(side="SHORT", entry_price=300, exit_price=299, qty=2, spec=spec) == 20
    assert risk_rub(entry_price=300, stop_price=301.5, qty=2, spec=spec) == 30


def test_invalid_multiplier_fails_closed():
    try:
        PnlUnitSpec("NGQ6@RTSX", "FUTURES", 0)
    except ValueError as exc:
        assert str(exc) == "PNL_UNIT_INVALID_MULTIPLIER"
    else:
        raise AssertionError("invalid multiplier must fail closed")
