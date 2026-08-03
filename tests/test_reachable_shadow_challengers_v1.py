from pathlib import Path


def test_challenger_registry_is_prospective_and_cannot_enable_trading() -> None:
    sql = Path("sql/analytics/273_reachable_shadow_challengers_v1.sql").read_text()
    source = Path("src/scripts/register_reachable_shadow_challengers_v1.py").read_text()
    assert "p.label_start_ts>=c.frozen_at" in sql
    assert "minimum_observations >= 20" in sql
    assert "minimum_active_days >= 3" in sql
    assert "paper_allowed boolean NOT NULL DEFAULT false CHECK (paper_allowed = false)" in sql
    assert "real_allowed boolean NOT NULL DEFAULT false CHECK (real_allowed = false)" in sql
    assert '"historical_diagnostics_reused": False' in source


def test_challengers_are_parallel_to_the_four_frozen_branches() -> None:
    source = Path("src/scripts/register_reachable_shadow_challengers_v1.py").read_text()
    for branch in (
        "SBER_LONG_M5_POST_FIX_V1",
        "BRQ6_SHORT_M5_POST_FIX_V1",
        "GLDRUBF_LONG_M5_POST_FIX_V1",
        "CNYRUBF_LONG_M5_POST_FIX_V1",
    ):
        assert branch in source
    assert "UPDATE analytics.v5_post_fix_branch_registry_v1" not in source
    assert "UPDATE analytics.v5_oos_run_v1" not in source
