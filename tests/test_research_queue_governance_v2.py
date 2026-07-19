from pathlib import Path


def test_queue_governor_is_db_scheduled_and_audited() -> None:
    migration = Path("sql/analytics/130_research_queue_governance_v2.sql").read_text()
    scheduler = Path("src/scripts/run_db_job_scheduler_v1.py").read_text()
    governor = Path("src/scripts/govern_research_queues_v2.py").read_text()

    assert "research_queue_governance_policy_v2" in migration
    assert "research_queue_governance_run_v2" in migration
    assert "RESEARCH_QUEUE_GOVERNOR_V2" in scheduler
    assert "SUPERSEDED_BY_DB_DRIVEN_RESEARCH_V2" in governor
    assert "DEDUPLICATED_BY_RESEARCH_QUEUE_GOVERNOR_V2" in governor
    assert "QUEUE_CAP_APPLIED_BY_RESEARCH_QUEUE_GOVERNOR_V2" in governor
    assert "priority_by_kind" in migration
    assert "command_request_v2_one_active_target_v2_idx" in migration
    assert "live_allowed=0" in governor
    worker = Path("src/marketcore/action/command_worker_v2.py").read_text()
    handler = Path("src/marketcore/action/handler_registry_v2.py").read_text()
    assert "ORDER BY priority,requested_at" in worker
    assert "target_id IS NOT DISTINCT FROM %s" in handler


def test_research_dashboard_counts_only_effective_pending_work() -> None:
    resolver = Path(
        "src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py"
    ).read_text()
    assert "status_code IN ('QUEUED','RUNNING')" in resolver
    assert "status_code NOT IN ('DONE','FAILED')" not in resolver
