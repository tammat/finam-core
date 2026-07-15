from __future__ import annotations

import argparse
import os
from collections import defaultdict
from datetime import date
from typing import Any

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.edge_validation_engine import EdgeValidationEngine
from finam_core.analytics.statistics_repository import build_psycopg_url


def migrate(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS analytics_edge_validation_v1 (
            id bigserial PRIMARY KEY,
            trade_date date NOT NULL,
            symbol text NOT NULL,
            strategy text NOT NULL,
            timeframe text NOT NULL,
            trades integer NOT NULL,
            pnl double precision NOT NULL,
            wins integer NOT NULL,
            losses integer NOT NULL,
            winrate double precision NOT NULL,
            profit_factor double precision NOT NULL,
            expectancy double precision NOT NULL,
            status text NOT NULL,
            reason text NOT NULL,
            calculated_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (trade_date, symbol, strategy, timeframe)
        );

        -- Superseded by the composite uniqueness contract above. Keeping the
        -- legacy symbol-only index rejects valid strategy/timeframe profiles.
        DROP INDEX IF EXISTS analytics_edge_validation_v1_symbol_uq;
        """)

        cur.execute("""
        CREATE OR REPLACE VIEW v_edge_validation_ru AS
        SELECT
            trade_date AS "Дата",
            symbol AS "Инструмент",
            strategy AS "Стратегия",
            timeframe AS "Таймфрейм",
            trades AS "Сделок",
            round(pnl::numeric, 6) AS "P&L",
            wins AS "Плюсовых",
            losses AS "Минусовых",
            round(winrate::numeric, 6) AS "Winrate",
            round(profit_factor::numeric, 6) AS "PF",
            round(expectancy::numeric, 6) AS "Expectancy",
            status AS "Статус edge",
            reason AS "Причина",
            calculated_at AS "Рассчитано"
        FROM analytics_edge_validation_v1
        ORDER BY trade_date DESC, symbol, strategy, timeframe;
        """)

        cur.execute("""
        CREATE OR REPLACE VIEW v_edge_validation_summary_ru AS
        SELECT
            trade_date AS "Дата",
            status AS "Статус edge",
            count(*) AS "Профилей",
            count(DISTINCT symbol) AS "Инструментов",
            count(DISTINCT strategy) AS "Стратегий"
        FROM analytics_edge_validation_v1
        GROUP BY trade_date, status
        ORDER BY trade_date DESC, status;
        """)


def load_rows(conn: psycopg.Connection, trade_date: date) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
        SELECT
            p.trade_date,
            p.symbol,
            COALESCE(NULLIF(t.strategy, ''), 'UNKNOWN') AS strategy,
            COALESCE(NULLIF(t.timeframe, ''), 'UNKNOWN') AS timeframe,
            p.trade_pnl
        FROM analytics_intraday_pnl p
        JOIN trades t ON t.id = p.trade_id
        WHERE p.trade_date = %s
          AND t.is_invalid = false
        ORDER BY p.symbol, strategy, timeframe, p.ts, p.trade_id
        """, (trade_date,))
        return [dict(r) for r in cur.fetchall()]


def save_results(
    conn: psycopg.Connection,
    trade_date: date,
    results: list[Any],
) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM analytics_edge_validation_v1 WHERE trade_date = %s", (trade_date,))

        for r in results:
            cur.execute("""
            INSERT INTO analytics_edge_validation_v1 (
                trade_date, symbol, strategy, timeframe,
                trades, pnl, wins, losses, winrate,
                profit_factor, expectancy, status, reason
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (trade_date, symbol, strategy, timeframe)
            DO UPDATE SET
                trades = EXCLUDED.trades,
                pnl = EXCLUDED.pnl,
                wins = EXCLUDED.wins,
                losses = EXCLUDED.losses,
                winrate = EXCLUDED.winrate,
                profit_factor = EXCLUDED.profit_factor,
                expectancy = EXCLUDED.expectancy,
                status = EXCLUDED.status,
                reason = EXCLUDED.reason,
                calculated_at = now()
            """, (
                trade_date,
                r.symbol,
                r.strategy,
                r.timeframe,
                r.trades,
                r.pnl,
                r.wins,
                r.losses,
                r.winrate,
                r.profit_factor,
                r.expectancy,
                r.status,
                r.reason,
            ))


def build_for_date(conn: psycopg.Connection, trade_date: date, min_trades: int) -> list[Any]:
    rows = load_rows(conn, trade_date)
    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)

    for row in rows:
        key = (
            str(row["symbol"]),
            str(row["strategy"]),
            str(row["timeframe"]),
        )
        grouped[key].append(float(row["trade_pnl"]))

    engine = EdgeValidationEngine()
    results = []

    for (symbol, strategy, timeframe), pnls in sorted(grouped.items()):
        results.append(
            engine.validate(
                symbol=symbol,
                strategy=strategy,
                timeframe=timeframe,
                pnls=pnls,
                min_trades=min_trades,
            )
        )

    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--min-trades", type=int, default=30)
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    trade_date = date.fromisoformat(args.date)
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url) as conn:
        if args.migrate:
            migrate(conn)

        results = build_for_date(conn, trade_date, args.min_trades)

        if args.save:
            save_results(conn, trade_date, results)

        conn.commit()

    print(
        f"EDGE_VALIDATION_TABLE_OK date={trade_date} profiles={len(results)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
