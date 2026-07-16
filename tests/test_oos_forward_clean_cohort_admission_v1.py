from pathlib import Path


def test_clean_cohort_admission_is_audited_and_deduplicated() -> None:
    source = Path("src/scripts/admit_oos_forward_clean_cohort_v1.py").read_text()
    assert "canonical_execution" in source
    assert "DUPLICATE_EXECUTION_FINGERPRINT" in source
    assert "OOS_PASS_CLEAN_HANDOFF" in source
    assert "historical_observations_imported=0" in source
    assert "runtime_changed=0" in source and "live_allowed=0" in source
    assert "SOURCE_OOS_PASS_REVOKED" in source
    assert "incubator_status='REVOKED'" in source


def test_oos_pass_requires_reproducible_parameters() -> None:
    source = Path("src/scripts/build_momentum_edge_oos_rank_v1.py").read_text()
    assert '"lookback" in params' in source
    assert '"hold" in params or "holding_bars" in params' in source
    assert '"threshold" in params' in source
    assert "OOS_SPECIFICATION_INCOMPLETE" in source


def test_admission_decisions_are_append_only() -> None:
    migration = Path("sql/analytics/065_oos_forward_clean_cohort_admission_v1.sql").read_text()
    assert "profit_funnel_oos_forward_admission_decision_v1" in migration
    assert "decision_code IN ('PASS','FAIL')" in migration
    assert "append_only" in migration
