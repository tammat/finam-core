from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(path): return (ROOT/path).read_text(encoding="utf-8")

def test_button_queues_and_does_not_directly_start_algorithm():
    renderer=read("src/marketcore/presentation/workspace_v2/renderer/control_center_v2_domain_renderer.py")
    controller=read("src/marketcore/presentation/action_http_controller_v2.py")
    assert '"research.edge_search.run", ActionKindV2.COMMAND' in renderer
    assert '_start_async_command_worker(request_id)' not in controller

def test_db_scheduler_executes_queue_in_low_load_window():
    migration=read("sql/analytics/084_edge_search_command_queue_v1.sql")
    scheduler=read("src/scripts/run_db_job_scheduler_v1.py")
    worker=read("src/marketcore/action/command_worker_v2.py")
    assert "EDGE_SEARCH_COMMAND_QUEUE_V1" in migration and "EDGE_SEARCH_COMMAND_QUEUE_V1" in scheduler
    assert "time '00:00',time '08:59'" in migration
    assert 'env["EDGE_SEARCH_FORCE"]' not in worker

def test_panel_has_steps_progress_and_persisted_results():
    resolver=read("src/marketcore/presentation/workspace_v2/resolver/control_center_v2_resolver.py")
    renderer=read("src/marketcore/presentation/workspace_v2/renderer/control_center_v2_domain_renderer.py")
    assert "def _edge_search_process" in resolver
    assert "progress_pct" in resolver
    assert "def _edge_search_results" in resolver
    assert '("edge_search_process", tuple(view_model.edge_search_process))' in renderer
    assert '("edge_search_results", tuple(view_model.edge_search_results))' in renderer
