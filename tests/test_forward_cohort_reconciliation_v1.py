from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]


def source(path: str) -> str:
    return (ROOT/path).read_text(encoding="utf-8")


def test_reconciliation_is_db_scheduled_before_forward_work() -> None:
    migration=source("sql/analytics/083_forward_cohort_reconciliation_v1.sql")
    scheduler=source("src/scripts/run_db_job_scheduler_v1.py")
    assert "FORWARD_COHORT_RECONCILIATION_V1" in migration
    assert "FORWARD_COHORT_RECONCILIATION_V1" in scheduler
    assert "'CURRENT'" in migration


def test_progress_uses_only_current_eligible_cohort() -> None:
    progress=source("src/scripts/build_forward_pass_progress_v1.py")
    gate=source("src/scripts/build_forward_edge_regime_promotion_gate_v1.py")
    assert "g.cohort_id=analytics.forward_edge_baseline_cohort_id_v1()" in progress
    assert "incubator_status IN ('ACCUMULATING','ROUTER_REQUIRED')" in progress
    assert "forward_edge_baseline_cohort_id_v1()" in gate


def test_admission_rejects_stale_market_data_auditably() -> None:
    admission=source("src/scripts/admit_oos_forward_clean_cohort_v1.py")
    assert "STALE_MARKET_DATA" in admission
    assert "freshness_limit_days" in admission
    assert "profit_funnel_oos_forward_admission_decision_v1" in admission


def test_no_candidate_state_is_visible_not_fake_progress() -> None:
    reconciler=source("src/scripts/reconcile_forward_cohort_v1.py")
    assert "NO_ELIGIBLE_FORWARD_CANDIDATES" in reconciler
    assert "TRUNCATE analytics.forward_pass_readiness_v1" in reconciler
    assert '"BLOCKED",0' in reconciler
