from pathlib import Path


def test_panel_sources_are_system_scheduled() -> None:
    migration=Path("sql/analytics/147_control_panel_source_freshness_v1.sql").read_text()
    scheduler=Path("src/scripts/run_db_job_scheduler_v1.py").read_text()
    for executor in ("SIGNAL_FUNNEL_ANALYTICS_V1","SIGNAL_FUNNEL_REASON_ANALYTICS_V1","MODEL_HEALTH_ENGINE_V1"):
        assert executor in migration
        assert executor in scheduler


def test_home_cards_distinguish_checkpoint_and_missing_diagnostics() -> None:
    source=Path("src/marketcore/presentation/workspace_v2/resolver/home_operator_dashboard_resolver_v1.py").read_text()
    assert '"SKIPPED": "Продолжится"' in source
    assert "Ожидается walk-forward" in source
    assert "WHERE model_health_snapshot_id=%s" in source
