from pathlib import Path


SEARCH_SCRIPTS = (
    "src/scripts/build_strategy_execution_runner_v1.py",
    "src/scripts/build_edge_hypothesis_discovery_v1.py",
    "src/scripts/build_edge_regime_hypothesis_discovery_v2.py",
    "src/scripts/build_walkforward_edge_search_v3.py",
)


def test_all_edge_search_paths_reject_untrusted_and_synthetic_bars():
    for script in SEARCH_SCRIPTS:
        source = Path(script).read_text()
        assert "source" in source
        assert "unknown" in source
        assert "synthetic_futures_backfill_v1" in source


def test_walkforward_filters_sources_in_universe_and_bar_load_queries():
    source = Path("src/scripts/build_walkforward_edge_search_v3.py").read_text()
    assert source.count("source NOT IN ('unknown','synthetic_futures_backfill_v1')") == 2
    assert "EDGE_SEARCH_TARGET_SYMBOL" in source
    assert "target_symbol=" in source
