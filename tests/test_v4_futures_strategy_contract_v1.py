from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_migration_has_explicit_assignments_and_closed_admission():
    sql = (ROOT / "sql/analytics/204_v4_futures_strategy_contract_v1.sql").read_text()
    for token in ("NGQ6@RTSX", "CNYRUBF@RTSX", "USDRUBF@RTSX", "GDU6@RTSX"):
        assert token in sql
    for strategy in ("CNY_REGIME_FUTURES", "USD_REGIME_FUTURES", "GOLD_TREND_BREAKOUT"):
        assert strategy in sql
    assert "false,0.80" in sql


def test_pipeline_requires_confirmed_regime_policy_and_orderbook_admission():
    source = (ROOT / "src/finam_core/pipelines/paper_pipeline.py").read_text()
    assert "FUTURES_REGIME_EVIDENCE_INCOMPLETE" in source
    assert "FUTURES_DB_POLICY_UNAVAILABLE" in source
    assert "MICROSTRUCTURE_UNAVAILABLE" in source
    assert "evaluate_futures_entry_cost_gate_v1" in source


def test_factory_knows_explicit_futures_models():
    source = (ROOT / "src/finam_core/strategy/strategy_factory.py").read_text()
    assert "CNY_REGIME_FUTURES" in source
    assert "USD_REGIME_FUTURES" in source
    assert "GOLD_TREND_BREAKOUT" in source


def test_symbol_resolver_normalizes_gold_and_fx():
    source = (ROOT / "src/finam_core/execution/execution_symbol_resolver.py").read_text()
    assert "GLDRUBF@RTSX" in source
    assert "GDU6@RTSX" in source
    assert "CNYRUB_CONT" in source
