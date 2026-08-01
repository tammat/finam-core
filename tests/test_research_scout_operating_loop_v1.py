from pathlib import Path
import uuid
import psycopg2
import psycopg2.extras

ROOT=Path(__file__).resolve().parents[1]

def test_scout_full_catalog_filters_and_single_click_are_wired():
    resolver=(ROOT/"src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py").read_text()
    renderer=(ROOT/"src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py").read_text()
    browser=(ROOT/"src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    assert "LIMIT 80" in resolver
    assert 'columns=("decision","symbol","category","score","capacity","correlation","bars","reason","action","status","operator_action")' in renderer
    assert "ensureScoutFilters" in browser and "applyScoutFilter" in browser
    assert '["all","Все"]' in browser
    assert 'endsWith(".operator_action")' in browser
    assert "this.openUniverseActions(element); return;" in browser

def test_scout_schedule_and_stale_monitor_are_db_driven():
    scheduler=(ROOT/"src/scripts/run_db_job_scheduler_v1.py").read_text()
    monitor=(ROOT/"src/scripts/monitor_research_processes_v1.py").read_text()
    migration=(ROOT/"sql/analytics/117_research_scout_operating_loop_v1.sql").read_text()
    assert '"RESEARCH_PROCESS_MONITOR_V1"' in scheduler
    assert "REQUEST_STALLED_PENDING" in monitor
    assert "PROCESS_HEARTBEAT_STALE" in monitor
    assert "RESEARCH_PROCESS_MONITOR" in migration
    service=(ROOT/"deploy/systemd/marketcore-db-job-scheduler.service").read_text()
    timer=(ROOT/"deploy/systemd/marketcore-db-job-scheduler.timer").read_text()
    assert "run_db_job_scheduler_v1.py" in service
    assert "REAL_TRADING_ENABLED=0" in service
    assert "OnUnitActiveSec=5min" in timer

def test_latest_scout_is_handed_to_next_universe_transactionally():
    from scripts.edge_research_universe_v1 import load_research_universe
    run_id=str(uuid.uuid4())
    connection=psycopg2.connect("postgresql:///finam_core")
    try:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            selected=load_research_universe(cursor,run_id=run_id,stage_code="TEST_SCOUT_HANDOFF",min_bars=5000,freshness_minutes=4320)
            symbols={row["symbol"] for row in selected}
            assert symbols
            cursor.execute("""WITH latest AS (
                SELECT run_id FROM analytics.instrument_scout_run_v1
                WHERE status_code='COMPLETE' ORDER BY started_at DESC LIMIT 1)
                SELECT symbol FROM analytics.instrument_scout_result_v1
                WHERE run_id=(SELECT run_id FROM latest) AND decision_code='SELECTED'""")
            scout_selected={row["symbol"] for row in cursor.fetchall()}
            assert scout_selected.issubset(symbols)
            source=(ROOT/"src/scripts/edge_research_universe_v1.py").read_text()
            assert "FOR UPDATE SKIP LOCKED" in source
    finally:
        connection.rollback(); connection.close()

def test_swing_next_plan_has_future_data_contract():
    source=(ROOT/"src/scripts/generate_next_swing_research_plan_v1.py").read_text()
    assert "confirmation_contract" in source
    assert "confirmation_after_ts,minimum_future_bars" in source
    assert '"D1":(30,20)' in source
