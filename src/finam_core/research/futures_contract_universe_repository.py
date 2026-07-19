from __future__ import annotations

import psycopg
from finam_core.analytics.statistics_repository import build_psycopg_url


class FuturesContractUniverseRepository:
    """Русский комментарий: хранит фьючерсные контракты с экспирациями."""

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or build_psycopg_url()

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS futures_contract_universe (
            id BIGSERIAL PRIMARY KEY,
            root_symbol TEXT NOT NULL,
            contract_symbol TEXT NOT NULL UNIQUE,
            asset_class TEXT NOT NULL DEFAULT 'futures',
            expiration_date DATE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            roll_priority INTEGER NOT NULL DEFAULT 100,
            status TEXT NOT NULL DEFAULT 'RESEARCH',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_futures_contract_universe_root
        ON futures_contract_universe(root_symbol, is_active, roll_priority);
        """
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def upsert_contract(
        self,
        *,
        root_symbol: str,
        contract_symbol: str,
        expiration_date: str,
        roll_priority: int,
        status: str = "RESEARCH",
    ) -> None:
        sql = """
        INSERT INTO futures_contract_universe (
            root_symbol, contract_symbol, expiration_date, roll_priority, status
        )
        VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT (contract_symbol)
        DO UPDATE SET
            root_symbol = EXCLUDED.root_symbol,
            expiration_date = EXCLUDED.expiration_date,
            roll_priority = EXCLUDED.roll_priority,
            status = EXCLUDED.status,
            updated_at = now()
        """
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (root_symbol, contract_symbol, expiration_date, roll_priority, status))
            conn.commit()

    def resolve_active_contract(
        self,
        *,
        root_symbol: str,
        roll_days: int = 5,
    ) -> str:
        """
        Русский комментарий:
        Выбирает ближайший активный контракт, исключая QUARANTINE
        и контракты, близкие к экспирации.
        """
        sql = """
        WITH latest_decision AS (
            SELECT selected_symbol AS contract_symbol,1 AS source_order,created_at
            FROM analytics.futures_roll_decision_v1
            WHERE root_symbol=%s AND selected_symbol IS NOT NULL
              AND created_at>=clock_timestamp()-interval '7 days'
            ORDER BY created_at DESC
            LIMIT 1
        ), calendar_fallback AS (
            SELECT symbol AS contract_symbol,2 AS source_order,updated_at AS created_at
            FROM public.futures_contract_calendar
            WHERE root_symbol=%s
              AND coalesce(last_trade_date,expiration_date)>CURRENT_DATE+(%s || ' days')::interval
            ORDER BY coalesce(last_trade_date,expiration_date),updated_at DESC
            LIMIT 1
        )
        SELECT contract_symbol FROM (
            SELECT * FROM latest_decision UNION ALL SELECT * FROM calendar_fallback
        ) chosen
        ORDER BY source_order,created_at DESC
        LIMIT 1
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (root_symbol, root_symbol, roll_days))
                row = cur.fetchone()

        return str(row[0]) if row else ""

    def resolve_research_contracts(
        self,
        *,
        root_symbol: str,
        max_contracts: int = 3,
    ) -> list[str]:
        """
        Русский комментарий:
        Возвращает несколько ближайших контрактов для research-наблюдения.
        QUARANTINE исключается.
        """
        sql = """
        SELECT symbol
        FROM public.futures_contract_calendar
        WHERE root_symbol = %s
          AND coalesce(last_trade_date,expiration_date) >= CURRENT_DATE
        ORDER BY coalesce(last_trade_date,expiration_date),updated_at DESC
        LIMIT %s
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (root_symbol, max_contracts))
                rows = cur.fetchall()

        return [str(row[0]) for row in rows]
