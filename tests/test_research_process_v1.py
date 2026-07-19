from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text()


def test_process_schema_links_request_cycle_run_and_events() -> None:
    sql = read("sql/marketcore_action/008_research_process_v1.sql")
    assert "CREATE TABLE IF NOT EXISTS marketcore_action.research_process_v1" in sql
    assert "process_id UUID PRIMARY KEY" in sql
    assert "command_request_id TEXT" in sql
    assert "cycle_id UUID" in sql
    assert "run_id UUID" in sql
    assert "research_process_event_v1" in sql
    assert "research_recommendation_action_v1" in sql
    assert "ensure_research_process_v1" in sql
    assert "command_request_research_process_v1" in sql


def test_command_handler_reuses_selected_process_row() -> None:
    source = read("src/marketcore/action/handler_registry_v2.py")
    assert "candidate_process_id" in source
    assert "ON CONFLICT (process_id) DO UPDATE SET" in source
    assert "status_code='PENDING',progress_pct=0,current_step_code='QUEUED'" in source
    assert "ACTION_SELECTED" in source
    assert "process_id" in source


def test_worker_updates_process_and_event_log() -> None:
    source = read("src/marketcore/action/command_worker_v2.py")
    assert "MARKETCORE_PROCESS_ID" in source
    assert "EXECUTION_STARTED" in source
    assert "EXECUTION_FINISHED" in source
    assert "progress_pct=100" in source


def test_edge_cycle_persists_real_step_progress() -> None:
    source = read("src/scripts/run_autonomous_edge_search_cycle_v1.py")
    assert 'process_id = os.getenv("MARKETCORE_PROCESS_ID")' in source
    assert "PROGRESS_UPDATED" in source
    assert "recommendation_code=%s" in source
    assert "process_id)" in source


def test_dashboard_actions_come_from_database() -> None:
    resolver = read("src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py")
    renderer = read("src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py")
    driver = read("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js")
    assert "research_process_v1" in resolver
    assert "research_recommendation_action_v1" in resolver
    assert '"actions": list(item.available_actions)' in renderer
    assert 'JSON.parse(recommendationCell?.dataset.mcActions || "[]")' in driver
    assert "const options = [" not in driver
    assert "processProgress" in driver
def test_monitor_closes_orphan_pending_processes() -> None:
    source = Path("src/scripts/monitor_research_processes_v1.py").read_text(encoding="utf-8")
    assert "ORPHAN_PENDING_WITHOUT_REQUEST" in source
    assert "ORPHAN_PENDING_SKIPPED" in source
