from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo


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


def test_heavy_search_has_session_and_resource_guards() -> None:
    source=Path("src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text()
    migration=Path("sql/analytics/078_edge_search_schedule_guard_v1.sql").read_text()
    assert "EDGE_SEARCH_OUTSIDE_LOW_LOAD_WINDOW" in source
    assert "EDGE_SEARCH_SERVER_LOAD_HIGH" in source
    assert "EDGE_SEARCH_MEMORY_RESERVE_LOW" in source
    assert "'RESOURCE_GUARD'" in source
    assert '"paper_shadow_priority_during_market_hours":true' in migration
    assert '"max_load_1m":2.5' in migration


def test_trading_hours_are_not_a_heavy_search_window() -> None:
    import importlib.util
    path=Path("src/scripts/run_autonomous_edge_search_cycle_v1.py")
    spec=importlib.util.spec_from_file_location("edge_cycle",path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    zone=ZoneInfo("Europe/Moscow")
    assert not module.heavy_search_window_open(datetime(2026,7,17,14,0,tzinfo=zone))
    assert module.heavy_search_window_open(datetime(2026,7,17,1,0,tzinfo=zone))
    assert module.heavy_search_window_open(datetime(2026,7,18,14,0,tzinfo=zone))
