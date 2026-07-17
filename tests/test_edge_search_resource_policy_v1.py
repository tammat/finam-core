from pathlib import Path


def test_search_runs_with_low_cpu_and_io_priority() -> None:
    wrapper=Path("deploy/run-autonomous-edge-search-v1.sh").read_text()
    assert "nice -n 15" in wrapper
    assert "ionice -c 2 -n 7" in wrapper


def test_database_declares_single_cycle_and_ui_protection() -> None:
    migration=Path("sql/analytics/076_edge_search_resource_policy_v1.sql").read_text()
    assert '"max_parallel_cycles":1' in migration
    assert '"estimated_cpu_cores":1' in migration
    assert '"protect_interactive_ui":true' in migration
    assert "executor_code='WALKFORWARD'" in migration and "timeout_seconds=3600" in migration


def test_cycle_still_has_database_advisory_lock() -> None:
    source=Path("src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text()
    assert "pg_try_advisory_lock" in source
    assert "AUTONOMOUS_EDGE_SEARCH_ALREADY_RUNNING" in source
