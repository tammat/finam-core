from __future__ import annotations

import argparse
import os
from collections import defaultdict
from typing import Any

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.edge_validation_engine import EdgeValidationEngine
from finam_core.analytics.statistics_repository import build_psycopg_url


def migrate(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS strategy_regime_matrix (
            id bigserial PRIMARY KEY,
            symbol text NOT NULL,
            strategy text NOT NULL,
            timeframe text NOT NULL,
            trade_source text NOT NULL,
            regime text NOT NULL,
            volatility_regime text NOT NULL,
            session_type text NOT NULL,
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
            UNIQUE (
                symbol, strategy, timeframe, trade_source,
                regime, volatility_regime, session_type
            )
        );
        """)

        # Русский комментарий:
        # Таблица могла существовать в старой схеме. CREATE TABLE IF NOT EXISTS
        # не добавляет новые поля, поэтому явно дорасширяем схему.
        cur.execute("ALTER TABLE strategy_regime_matrix ADD COLUMN IF NOT EXISTS volatility_regime text NOT NULL DEFAULT 'unknown';")
        cur.execute("ALTER TABLE strategy_regime_matrix ADD COLUMN IF NOT EXISTS session_type text NOT NULL DEFAULT 'unknown';")
        cur.execute("ALTER TABLE strategy_regime_matrix ADD COLUMN IF NOT EXISTS pnl double precision NOT NULL DEFAULT 0;")
        cur.execute("ALTER TABLE strategy_regime_matrix ADD COLUMN IF NOT EXISTS wins integer NOT NULL DEFAULT 0;")
        cur.execute("ALTER TABLE strategy_regime_matrix ADD COLUMN IF NOT EXISTS losses integer NOT NULL DEFAULT 0;")
        cur.execute("ALTER TABLE strategy_regime_matrix ADD COLUMN IF NOT EXISTS winrate double precision NOT NULL DEFAULT 0;")
        cur.execute("ALTER TABLE strategy_regime_matrix ADD COLUMN IF NOT EXISTS profit_factor double precision NOT NULL DEFAULT 0;")
        cur.execute("ALTER TABLE strategy_regime_matrix ADD COLUMN IF NOT EXISTS expectancy double precision NOT NULL DEFAULT 0;")
        cur.execute("ALTER TABLE strategy_regime_matrix ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'UNKNOWN';")
        cur.execute("ALTER TABLE strategy_regime_matrix ADD COLUMN IF NOT EXISTS reason text NOT NULL DEFAULT '';")
        cur.execute("ALTER TABLE strategy_regime_matrix ADD COLUMN IF NOT EXISTS trend text NOT NULL DEFAULT 'unknown';")
        cur.execute("ALTER TABLE strategy_regime_matrix ADD COLUMN IF NOT EXISTS volatility text NOT NULL DEFAULT 'unknown';")
        cur.execute("ALTER TABLE strategy_regime_matrix ADD COLUMN IF NOT EXISTS confidence double precision NOT NULL DEFAULT 0;")

        # Русский комментарий:
        # Старая schema strategy_regime_matrix содержит legacy NOT NULL поля.
        # Новый builder строит matrix из context_envelopes, поэтому legacy-поля
        # не должны блокировать insert.
        for column_name in [
            "exit_policy",
            "context_status",
            "runtime_action",
            "score_adjustment",
            "confidence_adjustment",
        ]:
            cur.execute(
                f"ALTER TABLE strategy_regime_matrix ALTER COLUMN {column_name} DROP NOT NULL;"
            )

        # Русский комментарий:
        # Legacy-колонки старой regime-matrix не должны ломать новый context-envelope builder.
        for column_name in [
            "exit_policy",
            "stop_policy",
            "take_policy",
            "risk_profile",
            "context_quality",
            "context_reason",
        ]:
            cur.execute(f"ALTER TABLE strategy_regime_matrix ADD COLUMN IF NOT EXISTS {column_name} text;")
            cur.execute(f"ALTER TABLE strategy_regime_matrix ALTER COLUMN {column_name} DROP NOT NULL;")

        # Русский комментарий:
        # Перед созданием unique index удаляем дубли старой схемы,
        # оставляя самую свежую строку по calculated_at/id.
        cur.execute("""
        DELETE FROM strategy_regime_matrix a
        USING strategy_regime_matrix b
        WHERE a.id < b.id
          AND a.symbol = b.symbol
          AND a.strategy = b.strategy
          AND a.timeframe = b.timeframe
          AND a.trade_source = b.trade_source
          AND a.regime = b.regime
          AND a.volatility_regime = b.volatility_regime
          AND a.session_type = b.session_type;
        """)

        # Русский комментарий:
        # Старые версии таблицы могли быть созданы без нового unique-ключа.
        # Он нужен для ON CONFLICT по режимному разрезу.
        cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_strategy_regime_matrix_context_v1
        ON strategy_regime_matrix (
            symbol,
            strategy,
            timeframe,
            trade_source,
            regime,
            volatility_regime,
            session_type
        );
        """)

        cur.execute("""
        CREATE OR REPLACE VIEW v_strategy_regime_matrix_ru AS
        SELECT
            symbol AS "Инструмент",
            strategy AS "Стратегия",
            timeframe AS "Таймфрейм",
            trade_source AS "Источник",
            regime AS "Режим",
            volatility_regime AS "Волатильность",
            session_type AS "Сессия",
            trades AS "Сделок",
            round(pnl::numeric, 6) AS "P&L",
            wins AS "Плюсовых",
            losses AS "Минусовых",
            round(winrate::numeric, 6) AS "Winrate",
            round(profit_factor::numeric, 6) AS "PF",
            round(expectancy::numeric, 6) AS "Expectancy",
            status AS "Статус",
            reason AS "Причина",
            calculated_at AS "Рассчитано"
        FROM strategy_regime_matrix
        ORDER BY symbol, strategy, timeframe, regime, volatility_regime, session_type;
        """)
        

def _json_text(payload: Any, key: str, default: str = "unknown") -> str:
    if isinstance(payload, dict):
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)
    return default


def load_rows(conn: psycopg.Connection, symbol: str, trade_source: str) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
        SELECT
            p.symbol,
            COALESCE(NULLIF(t.strategy, ''), 'UNKNOWN') AS strategy,
            COALESCE(NULLIF(t.timeframe, ''), 'UNKNOWN') AS timeframe,
            COALESCE(NULLIF(t.trade_source, ''), 'paper') AS trade_source,
            p.trade_pnl,
            e.regime,
            e.ts
        FROM analytics_intraday_pnl p
        JOIN trades t ON t.id = p.trade_id
        LEFT JOIN trade_context_envelopes e
               ON e.trade_date = p.trade_date
              AND e.trade_id = p.trade_id
        WHERE p.symbol = %s
          AND COALESCE(NULLIF(t.trade_source, ''), 'paper') = %s
          AND t.is_invalid = false
        ORDER BY p.ts, p.trade_id
        """, (symbol, trade_source))
        return [dict(r) for r in cur.fetchall()]


def build_matrix(conn: psycopg.Connection, symbol: str, trade_source: str, min_trades: int) -> list[tuple[Any, tuple[str, str, str, str, str, str, str]]]:
    rows = load_rows(conn, symbol=symbol, trade_source=trade_source)

    grouped: dict[tuple[str, str, str, str, str, str, str], list[float]] = defaultdict(list)

    for row in rows:
        regime_payload = row.get("regime") or {}

        regime = _json_text(regime_payload, "regime")
        volatility = _json_text(regime_payload, "volatility_regime")
        session = _json_text(regime_payload, "session_type")

        key = (
            str(row["symbol"]),
            str(row["strategy"]),
            str(row["timeframe"]),
            str(row["trade_source"]),
            regime,
            volatility,
            session,
        )
        grouped[key].append(float(row["trade_pnl"]))

    engine = EdgeValidationEngine()
    result: list[tuple[Any, tuple[str, str, str, str, str, str, str]]] = []

    for key, pnls in sorted(grouped.items()):
        symbol_, strategy, timeframe, trade_source_, regime, volatility, session = key
        edge = engine.validate(
            symbol=symbol_,
            strategy=strategy,
            timeframe=timeframe,
            pnls=pnls,
            min_trades=min_trades,
        )
        result.append((edge, key))

    return result


def save_matrix(conn: psycopg.Connection, symbol: str, trade_source: str, items: list[tuple[Any, tuple[str, str, str, str, str, str, str]]]) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM strategy_regime_matrix WHERE symbol = %s AND trade_source = %s",
            (symbol, trade_source),
        )

        saved = 0
        for edge, key in items:
            symbol_, strategy, timeframe, trade_source_, regime, volatility, session = key
            cur.execute("""
            INSERT INTO strategy_regime_matrix (
                symbol, strategy, timeframe, trade_source,
                regime, volatility_regime, session_type,
                trades, pnl, wins, losses, winrate,
                profit_factor, expectancy, status, reason,
                trend, volatility, confidence
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (
                symbol, strategy, timeframe, trade_source,
                regime, volatility_regime, session_type
            )
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
                trend = EXCLUDED.trend,
                volatility = EXCLUDED.volatility,
                confidence = EXCLUDED.confidence,
                calculated_at = now()
            """, (
                symbol_,
                strategy,
                timeframe,
                trade_source_,
                regime,
                volatility,
                session,
                edge.trades,
                edge.pnl,
                edge.wins,
                edge.losses,
                edge.winrate,
                edge.profit_factor,
                edge.expectancy,
                edge.status,
                edge.reason,
                regime,
                volatility,
                min(1.0, max(0.0, edge.profit_factor / 2.0 if edge.profit_factor < 999 else 1.0)),
            ))
            saved += 1

    return saved


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--trade-source", default="paper")
    parser.add_argument("--min-trades", type=int, default=30)
    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url) as conn:
        migrate(conn)
        items = build_matrix(
            conn=conn,
            symbol=args.symbol,
            trade_source=args.trade_source,
            min_trades=args.min_trades,
        )
        saved = save_matrix(
            conn=conn,
            symbol=args.symbol,
            trade_source=args.trade_source,
            items=items,
        )
        conn.commit()

    print(f"STRATEGY_REGIME_MATRIX_V1_OK symbol={args.symbol} saved={saved}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
