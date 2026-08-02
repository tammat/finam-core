from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return (ROOT/p).read_text(encoding="utf-8")
def test_cancel_is_governed_and_pending_only():
    registry=read("src/marketcore/action/handler_registry_v2.py")
    worker=read("src/marketcore/action/command_worker_v2.py")
    renderer=read("src/marketcore/presentation/workspace_v2/renderer/control_center_v2_domain_renderer.py")
    assert "RESEARCH.CANCEL_EDGE_SEARCH" in registry and "EDGE_SEARCH_CANCEL" in registry
    assert "request_kind='EDGE_SEARCH_RUN' AND status='PENDING'" in worker
    assert "research.edge_search.cancel" in renderer
def test_retry_is_once_and_technical_only():
    monitor=read("src/scripts/monitor_edge_search_command_queue_v1.py")
    sql=read("sql/marketcore_action/007_edge_search_cancel_retry_v1.sql")
    assert "edge_search_retry_v1" in sql
    assert "WORKER_COMMAND_FAILED:%" in monitor
    assert "parent_retry.retry_request_id=q.request_id" in monitor
    assert "technical_retry_created" in monitor
