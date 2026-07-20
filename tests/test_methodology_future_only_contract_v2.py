from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_contract_requires_future_only_non_overlapping_real_execution() -> None:
    sql = (ROOT / "sql/analytics/168_methodology_future_only_contract_v2.sql").read_text()
    assert '"future_only_required_for_remediation":true' in sql
    assert '"fold_overlap_forbidden":true' in sql
    assert '"min_microstructure_coverage":0.80' in sql
    assert '"min_independent_trade_days":5' in sql


def test_walkforward_records_auditable_methodology_evidence() -> None:
    source = (ROOT / "src/scripts/run_checkpointed_walkforward_v4.py").read_text()
    assert '"one_sided_p_value"' in source
    assert '"stressed_profit_factor"' in source
    assert '"microstructure_coverage"' in source
    assert '"independent_trade_days"' in source
    assert 'v.phase_code IN (\'FULL_OOS\',\'HOLDOUT\')' in source


def test_methodology_gate_reads_active_versioned_contract() -> None:
    source = (ROOT / "src/scripts/evaluate_edge_methodology_contract_v1.py").read_text()
    assert "WHERE active ORDER BY created_at DESC LIMIT 1" in source
    assert 'evidence.get("microstructure_coverage",0)' in source
    assert 'evidence.get("independent_trade_days",0)' in source
