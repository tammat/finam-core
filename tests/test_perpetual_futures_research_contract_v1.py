from pathlib import Path


ROOT = Path(__file__).parents[1]
SCOUT = (ROOT / "src/scripts/run_autonomous_instrument_scout_v1.py").read_text()
UNIVERSE = (ROOT / "src/scripts/edge_research_universe_v1.py").read_text()
SQL = (ROOT / "sql/analytics/190_perpetual_futures_research_contract_v1.sql").read_text()


def test_perpetual_symbols_are_db_configured() -> None:
    assert "USDRUBF@RTSX" in SQL
    assert "CNYRUBF@RTSX" in SQL
    assert "perpetual_symbols" in SQL


def test_scout_does_not_require_rollover_for_perpetuals() -> None:
    assert 'perpetual_symbols=set(policy.get("perpetual_symbols") or [])' in SCOUT
    assert "i.symbol = ANY(%s)" in SCOUT


def test_research_universe_does_not_require_expiration_for_perpetuals() -> None:
    assert "perpetual_symbols=list" in UNIVERSE
    assert "b.symbol=ANY(%s)" in UNIVERSE
