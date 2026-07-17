from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_auto_scheduler_persists_failures_and_never_enables_trading() -> None:
    source = (ROOT / "src/scripts/enqueue_scheduled_edge_search_v1.py").read_text()
    migration = (ROOT / "sql/analytics/088_edge_search_auto_heartbeat_v1.sql").read_text()
    assert "def record_failure" in source
    assert "last_error_code" in source and "SCHEDULER_ERROR" in source
    assert "EDGE_SEARCH_AUTO_ENQUEUE_V1_FAILED" in source
    assert "live_allowed=0" in source
    assert "ADD COLUMN IF NOT EXISTS last_error_code" in migration


def test_research_panel_shows_auto_scheduler_status() -> None:
    resolver = (ROOT / "src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py").read_text()
    renderer = (ROOT / "src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py").read_text()
    assert "edge_search_auto_schedule_state_v1" in resolver
    assert "edge_auto_status" in resolver
    assert '_status_tile("auto_status",s.edge_auto_status)' in renderer
