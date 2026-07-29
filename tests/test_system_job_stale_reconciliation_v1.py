from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_scheduler_reconciles_stale_running_only_after_lock() -> None:
    source = (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    lock = source.index("pg_try_advisory_lock")
    call = source.index("stale_runs = reconcile_stale_running_jobs")
    assert call > lock
    assert "schedule.timeout_seconds + 60" in source
    assert "SCHEDULER_RESTART_STALE_RUNNING_RECONCILED" in source
    assert "status_code='TIMEOUT'" in source


def test_migration_reconciles_existing_stale_row_without_deleting_audit() -> None:
    sql = (ROOT / "sql/analytics/225_system_job_stale_running_reconciliation_v1.sql").read_text()
    assert "status_code='TIMEOUT'" in sql
    assert "return_code=-2" in sql
    assert "schedule.timeout_seconds + 60" in sql
    assert "DELETE FROM analytics.system_job_run_v1" not in sql
