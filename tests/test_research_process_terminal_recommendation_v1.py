from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_terminal_recommendation_is_db_backed_and_has_no_action() -> None:
    migration = (ROOT / "sql/marketcore_action/150_research_process_terminal_recommendation_v1.sql").read_text(encoding="utf-8")
    worker = (ROOT / "src/marketcore/action/command_worker_v2.py").read_text(encoding="utf-8")
    assert "NO_ACTION_REQUIRED" in migration
    assert "status_code='SUCCEEDED'" in migration
    assert "recommendation_code='WAIT_FOR_SYSTEM_ANALYSIS'" in migration
    assert "finalize_research_recommendation_v1" in migration
    assert "NEW.outcome_code='CANCELLED'" in migration
    assert "THEN 'NO_ACTION_REQUIRED'" in worker
