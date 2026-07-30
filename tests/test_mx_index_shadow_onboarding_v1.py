from pathlib import Path


def test_mx_observer_is_allowlisted_and_shadow_only() -> None:
    scheduler = Path("src/scripts/run_db_job_scheduler_v1.py").read_text()
    migration = Path("sql/analytics/235_mx_index_shadow_onboarding_v1.sql").read_text()
    observer = Path("src/scripts/build_mx_index_shadow_observer_v1.py").read_text()
    assert '"MX_INDEX_SHADOW_OBSERVER_V1"' in scheduler
    assert "MXU6@RTSX" in migration
    assert "MX_INDEX_SHADOW_OBSERVER_V1" in migration
    assert "current, prior = bars[-1], bars[:-1]" in observer
    assert "paper_allowed=0 live_allowed=0" in observer
    assert "runtime_active_universe" not in migration
    assert "runtime_strategy_assignment_v1" not in migration
