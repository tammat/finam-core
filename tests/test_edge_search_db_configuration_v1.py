from pathlib import Path


SEARCH_SCRIPTS = (
    "build_edge_hypothesis_discovery_v1.py",
    "build_edge_regime_hypothesis_discovery_v2.py",
    "build_walkforward_edge_search_v3.py",
    "build_session_execution_edge_v1.py",
)


def test_all_searchers_load_algorithm_scenarios_from_database() -> None:
    sources = {name: Path("src/scripts", name).read_text() for name in SEARCH_SCRIPTS}
    assert "def load_search_configuration(cursor)" in sources[SEARCH_SCRIPTS[0]]
    assert "edge_search_algorithm_registry_v1" in sources[SEARCH_SCRIPTS[0]]
    for source in sources.values():
        assert "GRIDS" not in source
        assert "load_search_configuration" in source


def test_parameter_grids_regimes_and_gates_are_seeded_in_database() -> None:
    migration = Path("sql/analytics/072_edge_search_algorithm_config_v1.sql").read_text()
    for algorithm in ("MOMENTUM", "VWAP", "BOLLINGER", "RSI", "BREAKOUT"):
        assert algorithm in migration
    assert "allowed_regimes" in migration
    assert "min_profit_factor" in migration
    assert "final_holdout_required" in migration
    assert "parameter_grid=e.grid" in migration


def test_missing_or_empty_database_configuration_fails_closed() -> None:
    source = Path("src/scripts/build_edge_hypothesis_discovery_v1.py").read_text()
    assert "EDGE_SEARCH_ALGORITHM_CONFIG_MISSING" in source
    assert "EDGE_SEARCH_PARAMETER_GRID_EMPTY" in source
