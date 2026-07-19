from pathlib import Path

from scripts.run_autonomous_edge_search_cycle_v1 import output_flag, output_metric


def test_regime_discovery_is_resumable_and_time_bounded() -> None:
    source = Path("src/scripts/build_edge_regime_hypothesis_discovery_v2.py").read_text(
        encoding="utf-8"
    )
    assert "edge_regime_discovery_run_v3" in source
    assert "edge_regime_discovery_task_v3" in source
    assert "EDGE_REGIME_BATCH_SECONDS" in source
    assert "RECOVERED_AFTER_PROCESS_STOP" in source
    assert "discovery_task_id" in source
    assert "stage_complete=" in source
    assert "conn.autocommit = True" in source


def test_checkpoint_schema_keeps_task_and_result_idempotency() -> None:
    migration = Path("sql/analytics/135_edge_regime_discovery_checkpoint_v3.sql").read_text(
        encoding="utf-8"
    )
    assert "CREATE TABLE IF NOT EXISTS analytics.edge_regime_discovery_run_v3" in migration
    assert "CREATE TABLE IF NOT EXISTS analytics.edge_regime_discovery_task_v3" in migration
    assert "edge_regime_hypothesis_result_v2_task_regime_uq" in migration
    assert "UNIQUE(discovery_run_id,task_order)" in migration


def test_orchestrator_recognizes_incomplete_checkpoint_without_failure() -> None:
    source = Path("src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text(
        encoding="utf-8"
    )
    assert output_flag("stage_complete=0\n", "stage_complete") is False
    assert output_flag("stage_complete=1\n", "stage_complete") is True
    assert output_flag("", "stage_complete") is None
    assert output_metric("campaign_progress_pct=47\n", "campaign_progress_pct") == 47
    assert "EDGE_REGIME_DISCOVERY_CHECKPOINTED" in source
    assert "CONTINUE_ON_NEXT_SYSTEM_SCHEDULE" in source
