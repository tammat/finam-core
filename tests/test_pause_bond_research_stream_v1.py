from pathlib import Path


SQL = (Path(__file__).parents[1] / "sql/analytics/189_pause_bond_research_stream_v1.sql").read_text()


def test_bond_stream_is_parked_without_deleting_its_contract() -> None:
    assert "FRESH_V3_BONDS" in SQL
    assert "PAUSED_DATA_NOT_READY" in SQL
    assert "THEN 0.00" in SQL
    assert "THEN false" in SQL


def test_capacity_is_returned_to_active_streams() -> None:
    assert "FRESH_V3_EQUITY' THEN 0.60" in SQL
    assert "FRESH_V3_FUTURES' THEN 0.40" in SQL
    assert "'{category_quotas,BOND}', '0'::jsonb" in SQL
