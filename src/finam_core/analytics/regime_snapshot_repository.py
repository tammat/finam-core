from __future__ import annotations

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


class RegimeSnapshotRepository:
    """
    Русский комментарий:
    Хранит regime-снимки по инструменту и таймфрейму.
    v1 допускает ручную/скриптовую загрузку базового режима.
    """

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or build_psycopg_url()

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS regime_snapshots (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            ts TIMESTAMPTZ NOT NULL DEFAULT now(),

            regime TEXT NOT NULL DEFAULT 'unknown',
            trend TEXT NOT NULL DEFAULT 'unknown',
            volatility TEXT NOT NULL DEFAULT 'unknown',
            atr NUMERIC NOT NULL DEFAULT 0,

            source TEXT NOT NULL DEFAULT 'manual',

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            UNIQUE(symbol, timeframe, ts)
        );

        CREATE INDEX IF NOT EXISTS idx_regime_snapshots_symbol_ts
        ON regime_snapshots(symbol, timeframe, ts DESC);
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def save_snapshot(
        self,
        *,
        symbol: str,
        timeframe: str,
        regime: str,
        trend: str,
        volatility: str,
        atr: float = 0.0,
        source: str = "manual",
    ) -> None:
        sql = """
        INSERT INTO regime_snapshots (
            symbol, timeframe, regime, trend, volatility, atr, source
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (symbol, timeframe, regime, trend, volatility, atr, source),
                )
            conn.commit()
