from decimal import Decimal

from scripts.build_v5_hierarchical_evidence_v1 import initial_risk_cash


def test_futures_initial_risk_is_converted_to_cash_units() -> None:
    assert initial_risk_cash(
        entry_price="90.00",
        entry_stop_price="89.00",
        qty="2",
        risk_value_per_price_unit="798.573",
    ) == Decimal("1597.146")


def test_initial_risk_fails_closed_without_contract_spec() -> None:
    assert initial_risk_cash(
        entry_price="90.00",
        entry_stop_price="89.00",
        qty="1",
        risk_value_per_price_unit=None,
    ) == Decimal("0")
