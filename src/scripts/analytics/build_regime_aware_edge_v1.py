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
        CREATE TABLE IF NOT EXISTS analytics_regime_aware_edge_v1 (
            id bigserial PRIMARY KEY,
            trade_date date NOT NULL,
            symbol text NOT NULL,
            strategy text NOT NULL,
            timeframe text NOT NULL,
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
                trade_date, symbol, strategy, timeframe,
                regime, volatility_regime, session_type
            )
        );
        """)

        cur.execute("""
        CREATE OR REPLACE VIEW v_regime_aware_edge_ru AS
        SELECT
            trade_date AS "Дата",
            symbol AS "Инструмент",
            strategy AS "Стратегия",
            timeframe AS "Таймфрейм",
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
            status AS "Статус edge",
            reason AS "Причина",
            calculated_at AS "Рассчитано"
        FROM analytics_regime_aware_edge_v1
        ORDER BY trade_date DESC, symbol, strategy, timeframe, regime, volatility_regime, session_type;
        """)

        cur.execute("""
        CREATE OR REPLACE VIEW v_regime_aware_edge_summary_ru AS
        SELECT
            trade_date AS "Дата",
            regime AS "Режим",
            volatility_regime AS "Волатильность",
            status AS "Статус edge",
            count(*) AS "Профилей",
            count(DISTINCT symbol) AS "Инструментов",
            count(DISTINCT strategy) AS "Стратегий"
        FROM analytics_regime_aware_edge_v1
        GROUP BY trade_date, regime, volatility_regime, status
        ORDER BY trade_date DESC, regime, volatility_regime, status;
        """)


def _json_text(payload: Any, *keys: str, default: str = "unknown") -> str:
    # Русский комментарий:
    # Безопасно достает текстовое значение из jsonb/dict по нескольким возможным ключам.
    if not isinstance(payload, dict):
        return default

    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)

    return default


def _session_from_ts_msk(hour: int) -> str:
    # Русский комментарий:
    # Грубая классификация торговой сессии по Москве.
    if 7 <= hour < 10:
        return "morning"
    if 10 <= hour < 14:
        return "main_1"
    if 14 <= hour < 19:
        return "main_2"
    if 19 <= hour <= 23:
        return "evening"
    return "overnight"


def load_rows(conn: psycopg.Connection, trade_date: date) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
        SELECT
            p.trade_date,
            p.trade_id,
            p.ts,
            p.symbol,
            COALESCE(NULLIF(t.strategy, ''), 'UNKNOWN') AS strategy,
            COALESCE(NULLIF(t.timeframe, ''), 'UNKNOWN') AS timeframe,
            p.trade_pnl,
            e.regime,
            e.feature_snapshot,
            EXTRACT(HOUR FROM (p.ts AT TIME ZONE 'Europe/Moscow'))::int AS hour_msk
        FROM analytics_intraday_pnl p
        JOIN trades t ON t.id = p.trade_id
        LEFT JOIN trade_context_envelopes e
               ON e.trade_date = p.trade_date
              AND e.trade_id = p.trade_id
        WHERE p.trade_date = %s
          AND t.is_invalid = false
        ORDER BY p.symbol, strategy, timeframe, p.ts, p.trade_id
        """, (trade_date,))
        return [dict(r) for r in cur.fetchall()]


def classify_row(row: dict[str, Any]) -> tuple[str, str, str]:
    regime_payload = row.get("regime") or {}
    feature_payload = row.get("feature_snapshot") or {}

    regime = _json_text(
        regime_payload,
        "regime",
        "market_regime",
        "trend_regime",
        default="unknown",
    )

    volatility_regime = _json_text(
        regime_payload,
        "volatility",
        "volatility_regime",
        default=_json_text(feature_payload, "volatility_regime", "atr_state", default="unknown"),
    )

    session_type = _session_from_ts_msk(int(row.get("hour_msk") or 0))

    return regime, volatility_regime, session_type


def save_results(conn: psycopg.Connection, trade_date: date, results: list[Any], groups: list[tuple[str, str, str, str, str, str]]) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM analytics_regime_aware_edge_v1 WHERE trade_date = %s", (trade_date,))

        for result, group in zip(results, groups):
            symbol, strategy, timeframe, regime, volatility_regime, session_type = group
            cur.execute("""
            INSERT INTO analytics_regime_aware_edge_v1 (
                trade_date, symbol, strategy, timeframe,
                regime, volatility_regime, session_type,
                trades, pnl, wins, losses, winrate,
                profit_factor, expectancy, status, reason
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (
                trade_date, symbol, strategy, timeframe,
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
                calculated_at = now()
            """, (
                trade_date,
                symbol,
                strategy,
                timeframe,
                regime,
                volatility_regime,
                session_type,
                result.trades,
                result.pnl,
                result.wins,
                result.losses,
                result.winrate,
                result.profit_factor,
                result.expectancy,
                result.status,
                result.reason,
            ))


def build_for_date(conn: psycopg.Connection, trade_date: date, min_trades: int) -> tuple[list[Any], list[tuple[str, str, str, str, str, str]]]:
    rows = load_rows(conn, trade_date)
    grouped: dict[tuple[str, str, str, str, str, str], list[float]] = defaultdict(list)

    for row in rows:
        regime, volatility_regime, session_type = classify_row(row)
        key = (
            str(row["symbol"]),
            str(row["strategy"]),
            str(row["timeframe"]),
            regime,
            volatility_regime,
            session_type,
        )
        grouped[key].append(float(row["trade_pnl"]))

    engine = EdgeValidationEngine()
    groups: list[tuple[str, str, str, str, str, str]] = []
    results: list[Any] = []

    for group, pnls in sorted(grouped.items()):
        symbol, strategy, timeframe, regime, volatility_regime, session_type = group
        groups.append(group)
        results.append(
            engine.validate(
                symbol=symbol,
                strategy=strategy,
                timeframe=timeframe,
                pnls=pnls,
                min_trades=min_trades,
            )
        )

    return results, groups


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

        results, groups = build_for_date(conn, trade_date, args.min_trades)

        if args.save:
            save_results(conn, trade_date, results, groups)

        conn.commit()

    print(
        f"REGIME_AWARE_EDGE_V1_OK date={trade_date} profiles={len(results)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
