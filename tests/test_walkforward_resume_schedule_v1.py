from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_db_scheduler_can_resume_checkpointed_walkforward_in_short_slices():
    source = (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    assert '"CHECKPOINTED_WALKFORWARD_V4": "src/scripts/run_checkpointed_walkforward_v4.py"' in source
    assert '"CHECKPOINTED_WALKFORWARD_V4": {"WALKFORWARD_BATCH_SECONDS": "45"}' in source


def test_resume_schedule_respects_market_load_windows():
    migration = (ROOT / "sql/analytics/152_walkforward_checkpoint_resume_schedule_v1.sql").read_text()
    assert "WALKFORWARD_RESUME_MORNING" in migration
    assert "WALKFORWARD_RESUME_EVENING" in migration
    assert "WALKFORWARD_RESUME_WEEKEND" in migration
    assert "timeout_seconds, priority" in migration
