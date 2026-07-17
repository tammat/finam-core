from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_adaptive_generator_never_selects_on_final_holdout() -> None:
    source = (ROOT / "src/scripts/generate_adaptive_edge_search_scenarios_v1.py").read_text()
    assert 'int(item["fold"]) in (1, 2, 3, 4)' in source
    assert '"selection_uses_final_holdout": False' in source
    assert '"confirmation_mode": "FUTURE_DATA_ONLY"' in source
    assert "status_code='WAITING_FUTURE_DATA'" in source


def test_adaptive_scenarios_are_system_scheduled_and_bounded() -> None:
    runner = (ROOT / "src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text()
    migration = (ROOT / "sql/analytics/077_adaptive_edge_search_scenario_v1.sql").read_text()
    generator = (ROOT / "src/scripts/generate_adaptive_edge_search_scenarios_v1.py").read_text()
    assert '"GENERATE_ADAPTIVE_SCENARIOS"' in runner
    assert "'AUTONOMOUS_EDGE_SEARCH',12,'GENERATE_ADAPTIVE_SCENARIOS'" in migration
    assert 'ADAPTIVE_EDGE_MAX_NEW_SCENARIOS", "3"' in generator
    assert 'ADAPTIVE_EDGE_MIN_FUTURE_BARS", "500"' in generator


def test_active_scenario_is_symbol_scoped_and_auditable() -> None:
    loader = (ROOT / "src/scripts/build_edge_hypothesis_discovery_v1.py").read_text()
    assert "WHERE status_code='ACTIVE'" in loader
    assert '"adaptive_scenario_id"' in loader
    assert '"target_symbols": [row["target_symbol"]]' in loader
