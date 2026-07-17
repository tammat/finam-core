from pathlib import Path


def test_algorithm_analysis_is_a_required_database_scenario_step() -> None:
    migration=Path("sql/analytics/074_edge_search_algorithm_analysis_v1.sql").read_text()
    cycle=Path("src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text()
    assert "edge_search_algorithm_analysis_v1" in migration
    assert "'ANALYZE_RESULTS'" in migration
    assert '"ANALYZE_RESULTS": "src/scripts/analyze_edge_search_results_v1.py"' in cycle
    assert 'env["EDGE_SEARCH_WALKFORWARD_RUN_ID"]' in cycle


def test_analysis_preserves_reason_distribution_metrics_and_recommendation() -> None:
    source=Path("src/scripts/analyze_edge_search_results_v1.py").read_text()
    assert "reason_distribution" in source
    assert "best_metrics" in source
    assert "NEGATIVE_COST_ADJUSTED_EXPECTANCY" in source
    assert "REVIEW_SIGNAL_AND_COST_MODEL" in source
    assert "PROMOTE_CONFIRMED_PASS" in source


def test_analyzer_cannot_start_search_algorithms() -> None:
    source=Path("src/scripts/analyze_edge_search_results_v1.py").read_text()
    assert "subprocess" not in source
    assert "build_trades" not in source
