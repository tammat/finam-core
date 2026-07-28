from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_remediation_is_db_driven_bounded_and_auditable() -> None:
    sql = read("sql/analytics/207_instrument_data_remediation_queue_v1.sql")
    assert "enqueue_instrument_data_remediation_v1" in sql
    assert "instrument_data_remediation_status_v1" in sql
    assert "INSTRUMENT_DATA_REMEDIATION_V1" in sql
    for action in ("VERIFY_SPEC", "COLLECT_DATA", "COLLECT_LIQUIDITY", "MONITOR_ROLL"):
        assert action in sql
    assert "max_attempts integer NOT NULL DEFAULT 12" in sql
    assert "remediation_rank<=3" in sql
    assert "PARTITION BY r.category_code,r.next_action_code" in sql


def test_scout_enqueues_remediation_without_superseding_it() -> None:
    source = read("src/scripts/run_autonomous_instrument_scout_v1.py")
    assert "enqueue_instrument_data_remediation_v1" in source
    assert "status_code='PENDING' AND action_code='RESEARCH_NEXT'" in source
    assert "status_code IN ('PENDING','RETRY')" in source


def test_remediation_executor_is_checkpointed_and_registered() -> None:
    source = read("src/scripts/run_instrument_data_remediation_v1.py")
    scheduler = read("src/scripts/run_db_job_scheduler_v1.py")
    assert "FOR UPDATE SKIP LOCKED" in source
    assert "SAVEPOINT instrument_remediation_item" in source
    assert "market_data_watch_universe" in source
    assert "market_microstructure_aggregate_v1" in source
    assert '"INSTRUMENT_DATA_REMEDIATION_V1": "src/scripts/run_instrument_data_remediation_v1.py"' in scheduler


def test_research_panel_uses_remediation_progress() -> None:
    resolver = read("src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py")
    assert "instrument_scout_queue_v1 q" in resolver
    assert "rem.attempt_count" in resolver
    assert "rem.action_code" in resolver
