from __future__ import annotations

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


class ResearchRuntimeStateRepository:
    """
    Русский комментарий:
    Хранит состояние автономного research-supervisor.
    """

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or build_psycopg_url()

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS research_runtime_state (
            supervisor_name TEXT PRIMARY KEY,
            started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_cycle_at TIMESTAMPTZ,
            last_success_at TIMESTAMPTZ,
            status TEXT NOT NULL DEFAULT 'INIT',
            active_symbols TEXT NOT NULL DEFAULT '',
            failed_symbols TEXT NOT NULL DEFAULT '',
            last_error TEXT NOT NULL DEFAULT '',
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS research_runtime_cycle_log (
            id BIGSERIAL PRIMARY KEY,
            supervisor_name TEXT NOT NULL,
            started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            finished_at TIMESTAMPTZ,
            duration_sec NUMERIC NOT NULL DEFAULT 0,
            symbols TEXT NOT NULL DEFAULT '',
            trade_source TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'RUNNING',
            return_code INTEGER,
            error_message TEXT NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_research_runtime_cycle_log_started
        ON research_runtime_cycle_log(started_at DESC);

        CREATE INDEX IF NOT EXISTS idx_research_runtime_cycle_log_status
        ON research_runtime_cycle_log(status);
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def upsert_state(
        self,
        *,
        supervisor_name: str,
        status: str,
        active_symbols: str,
        failed_symbols: str = "",
        last_error: str = "",
        mark_success: bool = False,
    ) -> None:
        sql = """
        INSERT INTO research_runtime_state (
            supervisor_name,
            status,
            active_symbols,
            failed_symbols,
            last_error,
            last_cycle_at,
            last_success_at,
            updated_at
        )
        VALUES (
            %s,%s,%s,%s,%s,now(),
            CASE WHEN %s THEN now() ELSE NULL END,
            now()
        )
        ON CONFLICT (supervisor_name)
        DO UPDATE SET
            status = EXCLUDED.status,
            active_symbols = EXCLUDED.active_symbols,
            failed_symbols = EXCLUDED.failed_symbols,
            last_error = EXCLUDED.last_error,
            last_cycle_at = now(),
            last_success_at = CASE
                WHEN %s THEN now()
                ELSE research_runtime_state.last_success_at
            END,
            updated_at = now()
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        supervisor_name,
                        status,
                        active_symbols,
                        failed_symbols,
                        last_error,
                        mark_success,
                        mark_success,
                    ),
                )
            conn.commit()

    def start_cycle(
        self,
        *,
        supervisor_name: str,
        symbols: str,
        trade_source: str,
    ) -> int:
        sql = """
        INSERT INTO research_runtime_cycle_log (
            supervisor_name,
            symbols,
            trade_source,
            status
        )
        VALUES (%s,%s,%s,'RUNNING')
        RETURNING id
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (supervisor_name, symbols, trade_source))
                row = cur.fetchone()
            conn.commit()

        return int(row[0])

    def finish_cycle(
        self,
        *,
        cycle_id: int,
        duration_sec: float,
        return_code: int,
        status: str,
        error_message: str = "",
    ) -> None:
        sql = """
        UPDATE research_runtime_cycle_log
        SET
            finished_at = now(),
            duration_sec = %s,
            return_code = %s,
            status = %s,
            error_message = %s
        WHERE id = %s
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        duration_sec,
                        return_code,
                        status,
                        error_message,
                        cycle_id,
                    ),
                )
            conn.commit()
