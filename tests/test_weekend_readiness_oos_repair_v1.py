from pathlib import Path


def test_projection_quarantine_is_narrow_recoverable_and_fill_aware() -> None:
    sql=Path("sql/analytics/251_weekend_readiness_and_oos_repair_v1.sql").read_text()
    assert "paper_projection_quarantine_v1" in sql
    assert "p.symbol='TEST@MISX'" in sql
    assert "NOT EXISTS(SELECT 1 FROM signal_fills" in sql
    assert "NOT EXISTS(SELECT 1 FROM analytics.paper_research_position_lifecycle_v1" in sql
    assert "DELETE FROM analytics.paper_research_position_projection_v1" not in sql


def test_oos_permission_and_monday_schedule_are_explicit() -> None:
    sql=Path("sql/analytics/251_weekend_readiness_and_oos_repair_v1.sql").read_text()
    scheduler=Path("src/scripts/run_db_job_scheduler_v1.py").read_text()
    assert "GRANT INSERT,UPDATE ON analytics.trade_outcome_pattern_run_v1 TO finam" in sql
    assert "MONDAY_READINESS_V1" in scheduler
    assert "'[0]'::jsonb" in sql


def test_shock_replay_is_read_only_for_trading_and_uses_pre_entry_data() -> None:
    source=Path("src/scripts/analytics/build_market_shock_gate_replay_v1.py").read_text()
    assert "ts+interval '15 minutes'<=%s" in source
    assert "observed_at<=%s" in source
    assert "paper_changed=0 real_changed=0" in source
    assert "KEEP_SHADOW" in source
    assert "UPDATE analytics.entry_exit_runtime_profile" not in source


def test_ui_exposes_readiness_verdict() -> None:
    resolver=Path("src/marketcore/presentation/workspace_v2/resolver/control_compact_v3_resolver.py").read_text()
    renderer=Path("src/marketcore/presentation/workspace_v2/renderer/home_compact_v1_domain_renderer.py").read_text()
    assert "monday_readiness_snapshot_v1" in resolver
    assert "Готовность сессии" in renderer
