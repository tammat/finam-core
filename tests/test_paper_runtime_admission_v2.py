from pathlib import Path


def test_failed_oos_is_removed_from_active_paper() -> None:
    source = Path("src/scripts/build_profit_funnel_paper_runtime_admission_v2.py").read_text()
    assert "BLOCKED_OOS_FAIL" in source
    assert "c.candidate_status='OOS_FAIL' OR NOT c.paper_allowed" in source


def test_runtime_admission_is_pending_and_cannot_execute() -> None:
    source = Path("src/scripts/build_profit_funnel_paper_runtime_admission_v2.py").read_text()
    migration = Path("sql/analytics/058_profit_funnel_paper_runtime_admission_v2.sql").read_text()
    assert "AWAITING_RUNTIME_ADMISSION" in source
    assert "INSERT INTO public.runtime_observations" not in source
    assert "CHECK (NOT runtime_allowed AND NOT execution_enabled AND NOT live_allowed)" in migration
