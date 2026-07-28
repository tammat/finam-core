from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_generator_uses_one_full_fresh_scope_counter():
    source = (ROOT / "src/scripts/generate_trade_outcome_hypotheses_v1.py").read_text()
    assert "payload->'context'->>'cohort'='FRESH_V2'" in source
    assert "'FULL_SCOPE' AS scope" in source
    assert "strategy_code,side_code,symbol,session_code,regime_code,exit_rule" in source
    assert '"FRESH_V2_FULL_SCOPE"' in source
    assert '"WAITING_FRESH_DATA"' in source
    assert "MIN_TRADES" in source


def test_admission_requires_80_and_does_not_reopen_closed_request():
    source = (ROOT / "src/scripts/admit_trade_outcome_hypotheses_to_oos_v1.py").read_text()
    assert 'MIN_TRADES = int(os.getenv("TRADE_OUTCOME_HYPOTHESIS_MIN_TRADES", "80"))' in source
    assert '"WAITING_FRESH_DATA", "FRESH_SAMPLE_BELOW_80"' in source
    assert "minimum_closed_trades" in source
    assert "status_code <> 'CLOSED'" in source


def test_migration_preserves_legacy_rows_as_closed_audit_history():
    source = (ROOT / "sql/analytics/186_fresh_v2_cumulative_oos_v1.sql").read_text()
    assert "SUPERSEDED_BY_FRESH_V2_FULL_SCOPE" in source
    assert "lifecycle_state='CLOSED'" in source
    assert "interval_minutes=2" in source


def test_current_search_card_ignores_unrelated_failed_processes():
    source = (ROOT / "src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py").read_text()
    assert "AND p.process_type='EDGE_SEARCH'" in source
