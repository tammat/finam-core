from pathlib import Path


def test_timeout_is_persisted_as_technical_failure() -> None:
    source=Path("src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text()
    assert "except subprocess.TimeoutExpired" in source
    assert "EDGE_SEARCH_STEP_TIMEOUT:{executor_code}" in source
    assert "STEP_TIMEOUT_SECONDS=" in source
    assert "subprocess.CompletedProcess" in source


def test_stale_running_rows_are_reconciled_only_after_lock_is_acquired() -> None:
    source=Path("src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text()
    lock_position=source.index("if not cursor.fetchone()[0]:")
    reconcile_position=source.index("stale_runs = reconcile_stale_runs")
    assert reconcile_position > lock_position
    assert "EDGE_SEARCH_PROCESS_TERMINATED" in source
    assert "SYSTEM_PROCESS_TERMINATED_WITHOUT_FINAL_STATUS" in source
    assert "торговый результат не оценивался" in source
