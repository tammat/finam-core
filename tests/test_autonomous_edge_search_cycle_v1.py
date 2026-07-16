from pathlib import Path


def test_autonomous_cycle_searches_and_promotes_only_to_forward() -> None:
    source = Path("src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text()
    assert "pg_try_advisory_lock" in source
    assert "build_edge_regime_hypothesis_discovery_v2.py" in source
    assert "build_walkforward_edge_search_v3.py" in source
    assert "promote_regime_oos_to_canonical_v1.py" in source
    assert "admit_oos_forward_clean_cohort_v1.py" in source
    assert "build_profit_funnel_shadow_paper_admission_v2.py" in source
    assert "build_profit_funnel_paper_runtime_admission_v2.py" not in source
    assert '"REAL_TRADING_ENABLED": "0"' in source
    assert "live_allowed=0" in source


def test_autonomous_cycle_has_auditable_log_wrapper() -> None:
    wrapper = Path("deploy/run-autonomous-edge-search-v1.sh").read_text()
    assert "set -euo pipefail" in wrapper
    assert "autonomous-edge-search-v1.log" in wrapper
