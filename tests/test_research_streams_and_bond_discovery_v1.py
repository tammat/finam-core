from pathlib import Path


SQL = (Path(__file__).parents[1] / "sql/analytics/188_research_streams_and_bond_discovery_v1.sql").read_text()


def test_three_independent_research_streams_are_db_driven() -> None:
    assert "FRESH_V3_EQUITY" in SQL
    assert "FRESH_V3_FUTURES" in SQL
    assert "FRESH_V3_BONDS" in SQL
    assert "allocation_share" in SQL
    assert "0.50" in SQL and "0.35" in SQL and "0.15" in SQL


def test_bonds_start_in_discovery_and_cannot_trade_for_real() -> None:
    assert "'DATA_DISCOVERY', false, false" in SQL
    assert "'real_trading_enabled', false" in SQL
    assert "'activation_gate', 'DATA_AND_SPEC_READY'" in SQL


def test_bond_methodology_is_not_reduced_to_candles() -> None:
    for token in (
        "ACCRUED_INTEREST",
        "YIELD",
        "DURATION",
        "OFFER_AMORTIZATION",
        "CREDIT_RISK",
        "SPREAD",
        "VOLUME",
    ):
        assert token in SQL


def test_scout_has_bond_category_and_boards() -> None:
    assert "'BOND'" in SQL
    assert "'TQOB'" in SQL
    assert "'TQCB'" in SQL
    assert "'ofz_first', true" in SQL
