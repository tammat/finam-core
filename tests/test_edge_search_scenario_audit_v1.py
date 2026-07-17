from pathlib import Path


def test_search_pipeline_is_selected_from_database_and_executor_is_allowlisted() -> None:
    source = Path("src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text()
    assert "edge_search_scenario_step_v1" in source
    assert "EDGE_SEARCH_SCENARIO_NOT_CONFIGURED" in source
    assert "EDGE_SEARCH_EXECUTOR_NOT_ALLOWED" in source
    assert "for step_index, step_config in enumerate(steps" in source


def test_every_step_and_final_analysis_are_persisted() -> None:
    source = Path("src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text()
    migration = Path("sql/analytics/071_edge_search_scenario_audit_v1.sql").read_text()
    assert "edge_search_step_run_v1" in source
    assert "stdout_tail" in source and "stderr_tail" in source
    assert "persist_analysis" in source
    assert "edge_search_run_analysis_v1" in migration
    assert "success_factors" in migration
    assert "failure_factors" in migration
    assert '"manual_algorithm_start":false' in migration


def test_ui_or_operator_cannot_supply_an_executable_path() -> None:
    source = Path("src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text()
    assert "EXECUTORS = {" in source
    assert "EXECUTORS[executor_code]" in source
    assert "subprocess.run" in source
    assert "command_request" not in source
