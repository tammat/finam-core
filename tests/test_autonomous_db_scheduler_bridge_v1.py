from pathlib import Path


def test_existing_five_minute_timer_drives_db_owned_schedule() -> None:
    source = Path("src/scripts/run_market_universe_research_queue_cycle_v1.py").read_text()
    assert '"db_job_scheduler"' in source
    assert '"src/scripts/run_db_job_scheduler_v1.py"' in source
    assert '"VERDICT=DB_JOB_SCHEDULER_"' in source
