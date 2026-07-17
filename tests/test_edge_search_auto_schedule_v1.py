from pathlib import Path
from uuid import uuid4

import psycopg2


ROOT = Path(__file__).resolve().parents[1]


def test_auto_schedule_is_db_driven_low_load_and_idempotent() -> None:
    sql = (ROOT / "sql/analytics/086_edge_search_auto_schedule_v1.sql").read_text()
    source = (ROOT / "src/scripts/enqueue_scheduled_edge_search_v1.py").read_text()
    scheduler = (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    assert "EDGE_SEARCH_AUTO_NIGHT" in sql and "EDGE_SEARCH_AUTO_WEEKEND" in sql
    assert "time '00:00',time '08:59'" in sql
    assert "[5,6]" in sql and "time '00:00',time '23:59'" in sql
    assert "uuid.uuid5" in source
    assert "NO_NEW_MARKET_DATA" in source
    assert "ACTIVE_REQUEST_EXISTS" in source
    assert '"EDGE_SEARCH_AUTO_ENQUEUE_V1"' in scheduler
    assert "live_allowed=0" in source


def test_command_and_process_states_have_deferred_database_sync() -> None:
    sql = (ROOT / "sql/marketcore_action/009_command_process_state_sync_v1.sql").read_text()
    assert "DEFERRABLE INITIALLY DEFERRED" in sql
    assert "COMMAND_STATE_SYNCED" in sql
    assert "WHEN 'CANCELLED' THEN 'SKIPPED'" in sql
    assert "cycle_status='SKIPPED'" in sql


def test_empty_forward_remediation_is_waiting_not_failure() -> None:
    source = (ROOT / "src/scripts/generate_forward_remediation_scenarios_v1.py").read_text()
    assert "AWAITING_FORWARD_READINESS" in source
    assert "FORWARD_REMEDIATION_SCENARIOS_V1_OK" in source
    assert 'raise RuntimeError("FORWARD_REMEDIATION_NO_READINESS_DATA")' not in source


def test_database_syncs_cancelled_command_to_skipped_process() -> None:
    request_id = str(uuid4())
    try:
        with psycopg2.connect("postgresql:///finam_core") as connection:
            with connection.cursor() as cursor:
                cursor.execute("""INSERT INTO marketcore_action.command_request_v2
                    (request_id,action_id,request_kind,command_code,actor_id,status,requested_at)
                    VALUES(%s,'test.auto','RESEARCH_REFRESH','RESEARCH.REQUEST_REFRESH',
                           'test.auto','PENDING',clock_timestamp())""", (request_id,))
                cursor.execute("""UPDATE marketcore_action.command_request_v2
                    SET status='CANCELLED',finished_at=clock_timestamp() WHERE request_id=%s""", (request_id,))
        with psycopg2.connect("postgresql:///finam_core") as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT status_code,reason_code FROM marketcore_action.research_process_v1 WHERE process_id=%s::uuid", (request_id,))
                assert cursor.fetchone() == ("SKIPPED", "COMMAND_CANCELLED")
    finally:
        with psycopg2.connect("postgresql:///finam_core") as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM marketcore_action.command_request_v2 WHERE request_id=%s", (request_id,))
                cursor.execute("DELETE FROM marketcore_action.research_process_event_v1 WHERE process_id=%s::uuid", (request_id,))
                cursor.execute("DELETE FROM marketcore_action.research_process_v1 WHERE process_id=%s::uuid", (request_id,))
