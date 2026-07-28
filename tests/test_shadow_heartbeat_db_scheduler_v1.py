from datetime import datetime, timezone
from pathlib import Path
import importlib.util


def test_shadow_failure_is_persisted_outside_business_transaction() -> None:
    source=Path("src/scripts/run_forward_pass_shadow_observer_v2.py").read_text()
    assert "def record_started" in source
    assert "def record_failed" in source
    assert "last_failure_at=clock_timestamp()" in source
    assert "except BaseException as error" in source


def test_db_is_the_schedule_source_and_executor_is_allowlisted() -> None:
    source=Path("src/scripts/run_db_job_scheduler_v1.py").read_text()
    migration=Path("sql/analytics/080_shadow_heartbeat_db_scheduler_v1.sql").read_text()
    assert "analytics.system_job_schedule_v1" in source
    assert '"FORWARD_PASS_SHADOW_OBSERVER_V2"' in source
    assert "SYSTEM_JOB_EXECUTOR_NOT_ALLOWED" in source
    assert '"scheduler_job_code":"FORWARD_PASS_SHADOW_OBSERVER"' in migration


def test_unknown_research_executor_is_isolated_and_persisted() -> None:
    source=Path("src/scripts/run_db_job_scheduler_v1.py").read_text()
    assert "DB_JOB_SKIPPED" in source
    assert "status_code,\n                        return_code,stderr_tail,finished_at" in source
    assert "SYSTEM_JOB_EXECUTOR_NOT_ALLOWED:" in source
    assert "continue" in source


def test_due_uses_database_window_and_interval() -> None:
    path=Path("src/scripts/run_db_job_scheduler_v1.py")
    spec=importlib.util.spec_from_file_location("scheduler",path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    job={"timezone_code":"Europe/Moscow","weekdays":[0,1,2,3,4],
         "window_start":datetime.strptime("09:00","%H:%M").time(),
         "window_end":datetime.strptime("23:59","%H:%M").time(),"interval_minutes":5}
    now=datetime(2026,7,17,12,0,tzinfo=timezone.utc)
    assert module.due(job,now,None)
    assert not module.due(job,now,now)
