from pathlib import Path


def test_admission_uses_financial_and_sample_gates() -> None:
    source = Path("src/scripts/build_profit_funnel_shadow_paper_admission_v2.py").read_text()
    assert "net_pnl <= 0" in source
    assert "closed < min_obs" in source
    assert "days < min_days" in source
    assert "s.cohort_id=i.cohort_id" in source
    assert "INSERT INTO public.closed_trades" not in source


def test_admission_cannot_enable_execution() -> None:
    migration = Path("sql/analytics/057_profit_funnel_shadow_paper_admission_v2.sql").read_text()
    assert "CHECK (NOT paper_allowed AND NOT runtime_allowed AND NOT live_allowed)" in migration
    assert "UNIQUE (cohort_id,incubator_candidate_id)" in migration
