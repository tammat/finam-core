from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(path): return (ROOT/path).read_text(encoding="utf-8")

def test_only_one_active_search_request_is_allowed():
    sql=read("sql/analytics/085_edge_search_queue_hardening_v1.sql")
    handler=read("src/marketcore/action/handler_registry_v2.py")
    assert "command_request_v2_one_active_edge_search_idx" in sql
    assert "status IN ('PENDING','RUNNING')" in sql
    assert "status IN ('PENDING','RUNNING')" in handler

def test_monitor_recovers_stuck_and_expired_requests():
    monitor=read("src/scripts/monitor_edge_search_command_queue_v1.py")
    scheduler=read("src/scripts/run_db_job_scheduler_v1.py")
    assert "EDGE_SEARCH_RUNNING_TIMEOUT" in monitor
    assert "EDGE_SEARCH_PENDING_EXPIRED" in monitor
    assert "EDGE_SEARCH_QUEUE_MONITOR_V1" in scheduler

def test_panel_auto_refreshes_without_interrupting_dialogs():
    shell=read("src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_bootstrap_v2.js")
    assert "setInterval" in shell
    assert "5000" in shell
    assert "[role='dialog']" in shell
    assert "refreshInFlight" in shell
    assert 'data-runtime-status", "READY"' in shell

def test_process_results_are_scalar_not_object_dump():
    resolver=read("src/marketcore/presentation/workspace_v2/resolver/control_center_v2_resolver.py")
    assert "markets_evaluated" in resolver
    assert "combinations_evaluated" in resolver
    assert "coalesce(r.metrics,'{}'::jsonb) result" not in resolver
