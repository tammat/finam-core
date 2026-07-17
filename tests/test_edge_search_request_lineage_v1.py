from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding="utf-8")

def test_request_cycle_run_lineage_is_persisted():
    sql=read("sql/analytics/086_edge_search_request_lineage_v1.sql")
    runner=read("src/scripts/run_autonomous_edge_search_cycle_v1.py")
    worker=read("src/marketcore/action/command_worker_v2.py")
    assert "edge_search_request_run_v1" in sql
    assert "EDGE_SEARCH_REQUEST_ID" in worker
    assert "edge_search_request_run_v1" in runner

def test_pending_request_has_no_old_run_progress():
    resolver=read("src/marketcore/presentation/workspace_v2/resolver/control_center_v2_resolver.py")
    assert "latest[\"status\"] not in ('PENDING','CANCELLED')" in resolver
    assert "c.cycle_id=request.cycle_id" in resolver
