from __future__ import annotations

import argparse
import os
from datetime import date
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from finam_core.analytics.context_quality_engine import ContextQualityEngine
from finam_core.analytics.statistics_repository import build_psycopg_url


def migrate(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS trade_context_envelopes (
            id bigserial PRIMARY KEY,
            trade_date date NOT NULL,
            trade_id bigint NOT NULL,
            ts timestamptz NOT NULL,
            symbol text NOT NULL,
            strategy text NOT NULL,
            timeframe text NOT NULL,
            trade_source text NOT NULL,
            side text NOT NULL,
            qty double precision NOT NULL,
            price double precision NOT NULL,

            regime jsonb NOT NULL DEFAULT '{}'::jsonb,
            risk jsonb NOT NULL DEFAULT '{}'::jsonb,
            runtime jsonb NOT NULL DEFAULT '{}'::jsonb,
            execution jsonb NOT NULL DEFAULT '{}'::jsonb,
            strategy_context jsonb NOT NULL DEFAULT '{}'::jsonb,
            feature_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,

            context_quality text NOT NULL,
            missing_fields jsonb NOT NULL DEFAULT '[]'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),

            UNIQUE (trade_date, trade_id)
        );
        """)

        cur.execute("""
        CREATE OR REPLACE VIEW v_trade_context_envelopes_ru AS
        SELECT
            trade_date AS "Дата",
            ts AS "Время",
            symbol AS "Инструмент",
            strategy AS "Стратегия",
            timeframe AS "Таймфрейм",
            trade_source AS "Источник",
            side AS "Операция",
            qty AS "Количество",
            price AS "Цена",
            context_quality AS "Качество контекста",
            missing_fields AS "Недостающие поля",
            updated_at AS "Обновлено"
        FROM trade_context_envelopes
        ORDER BY ts DESC;
        """)

        cur.execute("""
        CREATE OR REPLACE VIEW v_trade_context_quality_summary_ru AS
        SELECT
            trade_date AS "Дата",
            context_quality AS "Качество контекста",
            count(*) AS "Сделок",
            count(DISTINCT symbol) AS "Инструментов",
            count(DISTINCT strategy) AS "Стратегий"
        FROM trade_context_envelopes
        GROUP BY trade_date, context_quality
        ORDER BY trade_date DESC, context_quality;
        """)


def _latest_json(conn: psycopg.Connection, table: str, symbol: str) -> dict[str, Any]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT exists (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema='public' AND table_name=%s
            )
            """,
            (table,),
        )
        if not cur.fetchone()["exists"]:
            return {}

        cur.execute(
            f"""
            SELECT to_jsonb(t.*) AS payload
            FROM {table} t
            WHERE symbol = %s
            ORDER BY ctid DESC
            LIMIT 1
            """,
            (symbol,),
        )
        row = cur.fetchone()
        return dict(row["payload"]) if row and isinstance(row["payload"], dict) else {}


def load_trades(conn: psycopg.Connection, trade_date: date) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
        SELECT
            id AS trade_id,
            (ts AT TIME ZONE 'Europe/Moscow')::date AS trade_date,
            ts,
            symbol,
            COALESCE(NULLIF(strategy, ''), 'UNKNOWN') AS strategy,
            COALESCE(NULLIF(timeframe, ''), 'UNKNOWN') AS timeframe,
            COALESCE(NULLIF(trade_source, ''), 'paper') AS trade_source,
            upper(side) AS side,
            qty,
            price,
            payload
        FROM trades
        WHERE (ts AT TIME ZONE 'Europe/Moscow')::date = %s
          AND is_invalid = false
        ORDER BY symbol, ts, id
        """, (trade_date,))
        return [dict(r) for r in cur.fetchall()]


def build_payload(conn: psycopg.Connection, row: dict[str, Any]) -> dict[str, Any]:
    symbol = row["symbol"]

    risk = _latest_json(conn, "trade_risk_context", symbol)
    runtime = _latest_json(conn, "runtime_strategy_selection", symbol)
    feature_snapshot = _latest_json(conn, "feature_snapshots", symbol)
    exit_policy = _latest_json(conn, "trade_exit_policy_context", symbol)
    regime = _latest_json(conn, "futures_mtf_regime", symbol)

    strategy_context = {
        "entry_reason": (row.get("payload") or {}).get("reason") if isinstance(row.get("payload"), dict) else None,
        "exit_policy": exit_policy,
    }

    return {
        "strategy": row["strategy"],
        "timeframe": row["timeframe"],
        "regime": regime,
        "risk": risk,
        "runtime": runtime,
        "execution": {
            "trade_source": row["trade_source"],
            "side": row["side"],
            "qty": row["qty"],
            "price": row["price"],
        },
        "strategy_context": strategy_context,
        "feature_snapshot": feature_snapshot,
    }


def save_envelopes(conn: psycopg.Connection, trade_date: date, rows: list[dict[str, Any]]) -> int:
    quality_engine = ContextQualityEngine()
    saved = 0

    with conn.cursor() as cur:
        cur.execute("DELETE FROM trade_context_envelopes WHERE trade_date = %s", (trade_date,))

        for row in rows:
            payload = build_payload(conn, row)
            quality = quality_engine.evaluate(payload)

            cur.execute("""
            INSERT INTO trade_context_envelopes (
                trade_date, trade_id, ts, symbol, strategy, timeframe, trade_source,
                side, qty, price,
                regime, risk, runtime, execution, strategy_context, feature_snapshot,
                context_quality, missing_fields
            )
            VALUES (
                %(trade_date)s, %(trade_id)s, %(ts)s, %(symbol)s, %(strategy)s, %(timeframe)s,
                %(trade_source)s, %(side)s, %(qty)s, %(price)s,
                %(regime)s, %(risk)s, %(runtime)s, %(execution)s, %(strategy_context)s, %(feature_snapshot)s,
                %(context_quality)s, %(missing_fields)s
            )
            ON CONFLICT (trade_date, trade_id)
            DO UPDATE SET
                regime = EXCLUDED.regime,
                risk = EXCLUDED.risk,
                runtime = EXCLUDED.runtime,
                execution = EXCLUDED.execution,
                strategy_context = EXCLUDED.strategy_context,
                feature_snapshot = EXCLUDED.feature_snapshot,
                context_quality = EXCLUDED.context_quality,
                missing_fields = EXCLUDED.missing_fields,
                updated_at = now()
            """, {
                **row,
                "regime": Jsonb(payload["regime"]),
                "risk": Jsonb(payload["risk"]),
                "runtime": Jsonb(payload["runtime"]),
                "execution": Jsonb(payload["execution"]),
                "strategy_context": Jsonb(payload["strategy_context"]),
                "feature_snapshot": Jsonb(payload["feature_snapshot"]),
                "context_quality": quality.quality,
                "missing_fields": Jsonb(quality.missing_fields),
            })
            saved += 1

    return saved


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    trade_date = date.fromisoformat(args.date)
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url) as conn:
        if args.migrate:
            migrate(conn)

        rows = load_trades(conn, trade_date)
        saved = save_envelopes(conn, trade_date, rows) if args.save else 0
        conn.commit()

    print(f"TRADE_CONTEXT_ENVELOPES_OK date={trade_date} rows={len(rows)} saved={saved}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
