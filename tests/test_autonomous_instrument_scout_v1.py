from pathlib import Path

import psycopg2


ROOT = Path(__file__).resolve().parents[1]


def test_scout_is_registered_in_db_scheduler():
    source = (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    assert '"INSTRUMENT_SCOUT_V1": "src/scripts/run_autonomous_instrument_scout_v1.py"' in source


def test_scout_run_is_complete_and_does_not_force_quiet_energy_contracts():
    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT run_id,status_code,discovered,selected
                FROM analytics.instrument_scout_run_v1 ORDER BY started_at DESC LIMIT 1""")
            run_id,status,discovered,selected=cursor.fetchone()
            assert status == "COMPLETE"
            assert discovered >= 500
            assert selected <= 10
            cursor.execute("""SELECT symbol,tradable_volatility_score,candidate_stage_code
                FROM analytics.instrument_scout_result_v1
                WHERE run_id=%s AND decision_code='SELECTED'
                  AND data_ready AND spec_ready AND liquidity_ready""",(run_id,))
            for symbol,score,stage in cursor.fetchall():
                assert score >= 45, symbol
                assert stage == "SHADOW_READY"
            cursor.execute("""SELECT count(*) FROM analytics.instrument_scout_queue_v1
                WHERE run_id=%s AND coalesce(evidence->>'promotion_ceiling','')<>'SHADOW'""",(run_id,))
            assert cursor.fetchone()[0] == 0


def test_scout_is_db_audited_and_bounded():
    migration=(ROOT / "sql/analytics/114_autonomous_instrument_scout_v1.sql").read_text()
    assert "instrument_scout_run_v1" in migration
    assert "instrument_scout_result_v1" in migration
    assert "instrument_scout_queue_v1" in migration
    assert '"max_new_watch_symbols_per_run":4' in migration


def test_research_v2_renders_scout_and_supports_row_actions():
    renderer=(ROOT / "src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py").read_text()
    browser=(ROOT / "src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    assert 'research.scout.title' in renderer
    assert '_scout_table(s.scout_items)' in renderer
    assert 'research\\.(?:universe\\.\\d+|scout\\.[a-z_]+\\.\\d+)' in browser
