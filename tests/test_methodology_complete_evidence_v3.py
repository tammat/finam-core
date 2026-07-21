from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v3_contract_requires_complete_execution_and_independence_evidence() -> None:
    sql = (ROOT / "sql/analytics/170_methodology_complete_evidence_v3.sql").read_text()
    assert "METHODOLOGY_V3_COMPLETE_EVIDENCE" in sql
    assert "'min_depth_coverage',0.80" in sql
    assert "'min_exchange_timestamp_coverage',0.80" in sql
    assert "'min_independent_sessions',2" in sql
    assert "'min_independent_regimes',2" in sql
    assert "pre_holdout_evidence" in sql


def test_walkforward_uses_order_book_exchange_time_and_pre_holdout_neighbors() -> None:
    source = (ROOT / "src/scripts/run_checkpointed_walkforward_v4.py").read_text()
    assert "m.bid_depth" in source
    assert "m.ask_depth" in source
    assert "m.exchange_ts" in source
    assert "source_latency_ms BETWEEN 0 AND 5000" in source
    assert "def _record_pre_holdout_robustness" in source
    assert '"pre_holdout_robust_neighbors"' in source
    assert '"independent_sessions"' in source
    assert '"independent_regimes"' in source


def test_methodology_gate_consumes_complete_evidence() -> None:
    source = (ROOT / "src/scripts/evaluate_edge_methodology_contract_v1.py").read_text()
    assert 'evidence.get("depth_coverage",0)' in source
    assert 'evidence.get("exchange_timestamp_coverage",0)' in source
    assert 'evidence.get("independent_sessions",0)' in source
    assert 'evidence.get("independent_regimes",0)' in source
    assert 'evidence.get("pre_holdout_robust_neighbors",0)' in source
    assert "cohort_integrity" in source
