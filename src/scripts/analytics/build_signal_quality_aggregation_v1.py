from __future__ import annotations

import os

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


def migrate(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS signal_quality_aggregation_v1 (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT,
            strategy TEXT,
            timeframe TEXT,
            session_type TEXT,
            regime TEXT,
            volatility_regime TEXT,

            signals_total BIGINT NOT NULL DEFAULT 0,
            filled_total BIGINT NOT NULL DEFAULT 0,
            closed_total BIGINT NOT NULL DEFAULT 0,
            wins BIGINT NOT NULL DEFAULT 0,
            losses BIGINT NOT NULL DEFAULT 0,
            flats BIGINT NOT NULL DEFAULT 0,

            winrate DOUBLE PRECISION,
            avg_pnl DOUBLE PRECISION,
            net_pnl DOUBLE PRECISION,
            gross_profit DOUBLE PRECISION,
            gross_loss DOUBLE PRECISION,
            profit_factor DOUBLE PRECISION,
            expectancy DOUBLE PRECISION,

            avg_confidence DOUBLE PRECISION,
            avg_rr DOUBLE PRECISION,
            avg_size_multiplier DOUBLE PRECISION,

            calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            UNIQUE (
                symbol,
                strategy,
                timeframe,
                session_type,
                regime,
                volatility_regime
            )
        );
        """)

        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_signal_quality_aggregation_v1_main
        ON signal_quality_aggregation_v1(symbol, strategy, timeframe);
        """)

        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_signal_quality_aggregation_v1_quality
        ON signal_quality_aggregation_v1(winrate, profit_factor, expectancy);
        """)

    conn.commit()


def build(conn: psycopg.Connection) -> int:
    with conn.cursor() as cur:
        cur.execute("""
        WITH grouped AS (
            SELECT
                symbol,
                strategy,
                timeframe,
                COALESCE(session_type, 'UNKNOWN') AS session_type,
                COALESCE(regime, 'UNKNOWN') AS regime,
                COALESCE(volatility_regime, 'UNKNOWN') AS volatility_regime,

                count(*) AS signals_total,
                count(*) FILTER (WHERE filled IS TRUE) AS filled_total,
                count(*) FILTER (WHERE outcome_class IN ('WIN', 'LOSS', 'FLAT')) AS closed_total,
                count(*) FILTER (WHERE outcome_class = 'WIN') AS wins,
                count(*) FILTER (WHERE outcome_class = 'LOSS') AS losses,
                count(*) FILTER (WHERE outcome_class = 'FLAT') AS flats,

                avg(pnl) FILTER (WHERE outcome_class IN ('WIN', 'LOSS', 'FLAT')) AS avg_pnl,
                sum(pnl) FILTER (WHERE outcome_class IN ('WIN', 'LOSS', 'FLAT')) AS net_pnl,
                sum(pnl) FILTER (WHERE pnl > 0) AS gross_profit,
                abs(sum(pnl) FILTER (WHERE pnl < 0)) AS gross_loss,

                avg(confidence) AS avg_confidence,
                avg(rr) AS avg_rr,
                avg(size_multiplier) AS avg_size_multiplier
            FROM signal_quality_audit_v1
            GROUP BY
                symbol,
                strategy,
                timeframe,
                COALESCE(session_type, 'UNKNOWN'),
                COALESCE(regime, 'UNKNOWN'),
                COALESCE(volatility_regime, 'UNKNOWN')
        )
        INSERT INTO signal_quality_aggregation_v1 (
            symbol,
            strategy,
            timeframe,
            session_type,
            regime,
            volatility_regime,
            signals_total,
            filled_total,
            closed_total,
            wins,
            losses,
            flats,
            winrate,
            avg_pnl,
            net_pnl,
            gross_profit,
            gross_loss,
            profit_factor,
            expectancy,
            avg_confidence,
            avg_rr,
            avg_size_multiplier,
            calculated_at
        )
        SELECT
            symbol,
            strategy,
            timeframe,
            session_type,
            regime,
            volatility_regime,
            signals_total,
            filled_total,
            closed_total,
            wins,
            losses,
            flats,
            CASE
                WHEN wins + losses > 0
                THEN wins::double precision / NULLIF(wins + losses, 0)
                ELSE NULL
            END AS winrate,
            avg_pnl,
            net_pnl,
            COALESCE(gross_profit, 0),
            COALESCE(gross_loss, 0),
            CASE
                WHEN COALESCE(gross_loss, 0) > 0
                THEN COALESCE(gross_profit, 0) / gross_loss
                ELSE NULL
            END AS profit_factor,
            CASE
                WHEN closed_total > 0
                THEN net_pnl / closed_total
                ELSE NULL
            END AS expectancy,
            avg_confidence,
            avg_rr,
            avg_size_multiplier,
            now()
        FROM grouped
        ON CONFLICT (
            symbol,
            strategy,
            timeframe,
            session_type,
            regime,
            volatility_regime
        )
        DO UPDATE SET
            signals_total = excluded.signals_total,
            filled_total = excluded.filled_total,
            closed_total = excluded.closed_total,
            wins = excluded.wins,
            losses = excluded.losses,
            flats = excluded.flats,
            winrate = excluded.winrate,
            avg_pnl = excluded.avg_pnl,
            net_pnl = excluded.net_pnl,
            gross_profit = excluded.gross_profit,
            gross_loss = excluded.gross_loss,
            profit_factor = excluded.profit_factor,
            expectancy = excluded.expectancy,
            avg_confidence = excluded.avg_confidence,
            avg_rr = excluded.avg_rr,
            avg_size_multiplier = excluded.avg_size_multiplier,
            calculated_at = now();
        """)

        affected = cur.rowcount

    conn.commit()
    return affected


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url) as conn:
        migrate(conn)
        saved = build(conn)

    print(f"SIGNAL_QUALITY_AGGREGATION_V1_OK saved={saved}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
