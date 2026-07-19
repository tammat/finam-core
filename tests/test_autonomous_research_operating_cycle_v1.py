from pathlib import Path


def test_operating_cycle_is_db_driven_and_visible() -> None:
    migration = Path("sql/analytics/143_autonomous_research_operating_cycle_v1.sql").read_text()
    resolver = Path("src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py").read_text()
    renderer = Path("src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py").read_text()
    for table in ("market_session_policy_v1", "market_open_readiness_v1", "historical_edge_audit_schedule_state_v1"):
        assert table in migration
    assert "market_open_readiness_v1" in resolver
    assert "historical_edge_audit_schedule_state_v1" in resolver
    readiness = Path("src/scripts/check_market_open_readiness_v1.py").read_text()
    assert "market_session_policy_v1" in readiness
    assert '"research.operating"' in renderer
    assert "next_session_at" in resolver


def test_scheduler_knows_safe_new_executors() -> None:
    scheduler = Path("src/scripts/run_db_job_scheduler_v1.py").read_text()
    assert '"MARKET_OPEN_READINESS_V1"' in scheduler
    assert '"HISTORICAL_EDGE_AUDIT_ENQUEUE_V1"' in scheduler
    assert "check_market_open_readiness_v1.py" in scheduler
    assert "enqueue_historical_edge_audit_v1.py" in scheduler


def test_historical_audit_is_enqueued_not_executed_inline() -> None:
    source = Path("src/scripts/enqueue_historical_edge_audit_v1.py").read_text()
    assert "marketcore_action.command_request_v2" in source
    assert "system.historical_audit" in source
    assert "subprocess" not in source
    assert "REAL_TRADING" not in source
