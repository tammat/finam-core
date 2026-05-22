from __future__ import annotations

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


class FuturesContextNormalizer:
    """
    Русский комментарий:
    Нормализует фьючерсные контракты до root-инструмента.
    Не меняет исходный symbol, а добавляет контекст экспирации.
    """

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or build_psycopg_url()

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS futures_context_snapshots (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            root_symbol TEXT NOT NULL,
            contract_symbol TEXT NOT NULL,
            expiration_date DATE,
            days_to_expiration INTEGER,
            status TEXT NOT NULL DEFAULT 'UNKNOWN',
            source TEXT NOT NULL DEFAULT 'futures_contract_universe',
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            UNIQUE(symbol)
        );

        CREATE INDEX IF NOT EXISTS idx_futures_context_root
        ON futures_context_snapshots(root_symbol);

        CREATE INDEX IF NOT EXISTS idx_futures_context_expiration
        ON futures_context_snapshots(expiration_date);
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def rebuild(self) -> int:
        sql = """
        INSERT INTO futures_context_snapshots (
            symbol,
            root_symbol,
            contract_symbol,
            expiration_date,
            days_to_expiration,
            status,
            source,
            updated_at
        )
        SELECT
            contract_symbol AS symbol,
            root_symbol,
            contract_symbol,
            expiration_date,
            CASE
                WHEN expiration_date IS NULL THEN NULL
                ELSE (expiration_date - CURRENT_DATE)::int
            END AS days_to_expiration,
            status,
            'futures_contract_universe',
            now()
        FROM futures_contract_universe
        ON CONFLICT (symbol)
        DO UPDATE SET
            root_symbol = EXCLUDED.root_symbol,
            contract_symbol = EXCLUDED.contract_symbol,
            expiration_date = EXCLUDED.expiration_date,
            days_to_expiration = EXCLUDED.days_to_expiration,
            status = EXCLUDED.status,
            source = EXCLUDED.source,
            updated_at = now()
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                affected = cur.rowcount
            conn.commit()

        return int(affected or 0)
