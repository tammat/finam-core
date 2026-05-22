from __future__ import annotations

from datetime import datetime, timezone
import time

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


class ResearchPipelineRunLog:
    """
    Русский комментарий:
    Журнал запусков research pipeline и его шагов.
    Нужен для диагностики, Grafana и последующего supervisor/runtime.
    """

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or build_psycopg_url()

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS research_pipeline_runs (
            id BIGSERIAL PRIMARY KEY,
            started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            finished_at TIMESTAMPTZ,
            trade_source TEXT NOT NULL DEFAULT '',
            symbols_total INTEGER NOT NULL DEFAULT 0,
            symbols_ok INTEGER NOT NULL DEFAULT 0,
            symbols_failed INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'RUNNING',
            error_message TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS research_pipeline_step_events (
            id BIGSERIAL PRIMARY KEY,
            run_id BIGINT NOT NULL REFERENCES research_pipeline_runs(id) ON DELETE CASCADE,
            symbol TEXT NOT NULL DEFAULT '',
            step_name TEXT NOT NULL,
            command TEXT NOT NULL DEFAULT '',
            started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            finished_at TIMESTAMPTZ,
            status TEXT NOT NULL DEFAULT 'RUNNING',
            return_code INTEGER,
            duration_sec NUMERIC NOT NULL DEFAULT 0,
            error_message TEXT NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_research_pipeline_runs_status
        ON research_pipeline_runs(status, started_at DESC);

        CREATE INDEX IF NOT EXISTS idx_research_pipeline_steps_run
        ON research_pipeline_step_events(run_id, started_at);

        CREATE INDEX IF NOT EXISTS idx_research_pipeline_steps_symbol
        ON research_pipeline_step_events(symbol, started_at DESC);
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def start_run(self, *, trade_source: str, symbols_total: int) -> int:
        sql = """
        INSERT INTO research_pipeline_runs (
            trade_source,
            symbols_total,
            status
        )
        VALUES (%s, %s, 'RUNNING')
        RETURNING id
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (trade_source, symbols_total))
                row = cur.fetchone()
            conn.commit()

        return int(row[0])

    def finish_run(
        self,
        *,
        run_id: int,
        symbols_ok: int,
        symbols_failed: int,
        status: str,
        error_message: str = "",
    ) -> None:
        sql = """
        UPDATE research_pipeline_runs
        SET
            finished_at = now(),
            symbols_ok = %s,
            symbols_failed = %s,
            status = %s,
            error_message = %s
        WHERE id = %s
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        symbols_ok,
                        symbols_failed,
                        status,
                        error_message,
                        run_id,
                    ),
                )
            conn.commit()

    def start_step(
        self,
        *,
        run_id: int,
        symbol: str,
        step_name: str,
        command: str,
    ) -> int:
        sql = """
        INSERT INTO research_pipeline_step_events (
            run_id,
            symbol,
            step_name,
            command,
            status
        )
        VALUES (%s, %s, %s, %s, 'RUNNING')
        RETURNING id
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (run_id, symbol, step_name, command))
                row = cur.fetchone()
            conn.commit()

        return int(row[0])

    def finish_step(
        self,
        *,
        step_id: int,
        return_code: int,
        duration_sec: float,
        error_message: str = "",
    ) -> None:
        status = "OK" if return_code == 0 else "FAILED"

        sql = """
        UPDATE research_pipeline_step_events
        SET
            finished_at = now(),
            status = %s,
            return_code = %s,
            duration_sec = %s,
            error_message = %s
        WHERE id = %s
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        status,
                        return_code,
                        duration_sec,
                        error_message,
                        step_id,
                    ),
                )
            conn.commit()

    @staticmethod
    def monotonic() -> float:
        return time.monotonic()

    @staticmethod
    def now_utc() -> datetime:
        return datetime.now(timezone.utc)
