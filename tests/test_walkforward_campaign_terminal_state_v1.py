import os

import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def test_complete_phase_cannot_remain_running() -> None:
    with psycopg2.connect(DB) as connection, connection.cursor() as cursor:
        cursor.execute("""
          SELECT count(*) FROM analytics.walkforward_campaign_v4
          WHERE phase_code='COMPLETE' AND status_code<>'COMPLETE'
        """)
        assert cursor.fetchone()[0] == 0


def test_terminal_state_guard_is_installed() -> None:
    with psycopg2.connect(DB) as connection, connection.cursor() as cursor:
        cursor.execute("""
          SELECT count(*) FROM pg_trigger
          WHERE tgrelid='analytics.walkforward_campaign_v4'::regclass
            AND tgname='trg_walkforward_campaign_terminal_state_v1'
            AND NOT tgisinternal
        """)
        assert cursor.fetchone()[0] == 1
