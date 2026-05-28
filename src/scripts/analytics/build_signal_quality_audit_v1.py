from __future__ import annotations

import argparse
import os
from datetime import date

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from finam_core.analytics.statistics_repository import build_psycopg_url


def migrate(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS signal_quality_audit_v1 (
            id BIGSERIAL PRIMARY KEY,
            signal_id TEXT NOT NULL UNIQUE,
            signal_ts TIMESTAMPTZ,
            symbol TEXT,
            side TEXT,
            strategy TEXT,
            timeframe TEXT,
            horizon TEXT,
            regime TEXT,
            volatility_regime TEXT,
            session_type TEXT,
            confidence DOUBLE PRECISION,
            rr DOUBLE PRECISION,
            size_multiplier DOUBLE PRECISION,
            entry_price DOUBLE PRECISION,
            stop_loss DOUBLE PRECISION,
            take_profit DOUBLE PRECISION,
            qty DOUBLE PRECISION,
            filled BOOLEAN NOT NULL DEFAULT FALSE,
            fill_id TEXT,
            fill_price DOUBLE PRECISION,
            trade_id BIGINT,
            pnl DOUBLE PRECISION,
            win BOOLEAN,
            outcome_class TEXT NOT NULL DEFAULT 'UNKNOWN',
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            calculated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_signal_quality_audit_v1_symbol
        ON signal_quality_audit_v1(symbol);
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_signal_quality_audit_v1_regime
        ON signal_quality_audit_v1(regime, volatility_regime, session_type);
        """)
    conn.commit()


def classify_outcome(filled: bool, pnl: float | None) -> str:
    if not filled:
        return "NOT_FILLED"
    if pnl is None:
        return "FILLED_NO_PNL"
    if pnl > 0:
        return "WIN"
    if pnl < 0:
        return "LOSS"
    return "FLAT"


def build(conn: psycopg.Connection, trade_date: date | None = None) -> int:
    where = []
    params = []

    if trade_date:
        where.append("(s.ts AT TIME ZONE 'Europe/Moscow')::date = %s")
        params.append(trade_date)

    where_sql = "WHERE " + " AND ".join(where) if where else ""

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"""
        WITH src AS (
            SELECT
                COALESCE(s.signal_id, 'legacy_signal_' || s.id::text) AS signal_id,
                s.ts AS signal_ts,
                s.symbol,
                upper(s.side) AS side,
                s.strategy,
                s.timeframe,
                s.horizon,
                COALESCE(
                    s.regime,
                    s.payload->'signal_quality_snapshot'->>'regime',
                    s.payload->'features'->>'regime'
                ) AS regime,
                COALESCE(
                    s.payload->'signal_quality_snapshot'->>'volatility_regime',
                    s.payload->'features'->>'volatility_regime'
                ) AS volatility_regime,
                COALESCE(
                    s.payload->'signal_quality_snapshot'->>'session_type',
                    s.payload->'features'->>'session_type'
                ) AS session_type,
                COALESCE(
                    s.confidence,
                    NULLIF(s.payload->'signal_quality_snapshot'->>'confidence', '')::double precision,
                    NULLIF(s.payload->'features'->>'confidence', '')::double precision
                ) AS confidence,
                s.rr,
                NULLIF(s.payload->'signal_quality_snapshot'->>'size_multiplier', '')::double precision AS size_multiplier,
                s.entry_price,
                s.stop_loss,
                s.take_profit,
                NULLIF(s.payload->>'qty', '')::double precision AS qty,
                s.payload
            FROM signals s
            {where_sql}
        ),
        linked AS (
            SELECT
                src.*,
                sf.fill_id,
                sf.price AS fill_price,
                t.id AS trade_id,
                t.price AS trade_price,
                p.trade_pnl AS pnl
            FROM src
            LEFT JOIN signal_fills sf
              ON sf.signal_id = src.signal_id
            LEFT JOIN trades t
              ON t.fill_id = sf.fill_id
              OR t.payload->>'signal_id' = src.signal_id
            LEFT JOIN analytics_intraday_pnl p
              ON p.trade_id = t.id
        )
        SELECT *
        FROM linked
        """, params)

        rows = [dict(r) for r in cur.fetchall()]

    saved = 0

    with conn.cursor() as cur:
        for r in rows:
            filled = bool(r.get("fill_id") or r.get("trade_id"))
            pnl = r.get("pnl")
            outcome = classify_outcome(filled, pnl)

            cur.execute("""
            INSERT INTO signal_quality_audit_v1 (
                signal_id,
                signal_ts,
                symbol,
                side,
                strategy,
                timeframe,
                horizon,
                regime,
                volatility_regime,
                session_type,
                confidence,
                rr,
                size_multiplier,
                entry_price,
                stop_loss,
                take_profit,
                qty,
                filled,
                fill_id,
                fill_price,
                trade_id,
                pnl,
                win,
                outcome_class,
                payload,
                calculated_at
            )
            VALUES (
                %(signal_id)s,
                %(signal_ts)s,
                %(symbol)s,
                %(side)s,
                %(strategy)s,
                %(timeframe)s,
                %(horizon)s,
                %(regime)s,
                %(volatility_regime)s,
                %(session_type)s,
                %(confidence)s,
                %(rr)s,
                %(size_multiplier)s,
                %(entry_price)s,
                %(stop_loss)s,
                %(take_profit)s,
                %(qty)s,
                %(filled)s,
                %(fill_id)s,
                %(fill_price)s,
                %(trade_id)s,
                %(pnl)s,
                %(win)s,
                %(outcome_class)s,
                %(payload)s::jsonb,
                now()
            )
            ON CONFLICT (signal_id)
            DO UPDATE SET
                signal_ts = excluded.signal_ts,
                symbol = excluded.symbol,
                side = excluded.side,
                strategy = excluded.strategy,
                timeframe = excluded.timeframe,
                horizon = excluded.horizon,
                regime = excluded.regime,
                volatility_regime = excluded.volatility_regime,
                session_type = excluded.session_type,
                confidence = excluded.confidence,
                rr = excluded.rr,
                size_multiplier = excluded.size_multiplier,
                entry_price = excluded.entry_price,
                stop_loss = excluded.stop_loss,
                take_profit = excluded.take_profit,
                qty = excluded.qty,
                filled = excluded.filled,
                fill_id = excluded.fill_id,
                fill_price = excluded.fill_price,
                trade_id = excluded.trade_id,
                pnl = excluded.pnl,
                win = excluded.win,
                outcome_class = excluded.outcome_class,
                payload = excluded.payload,
                calculated_at = now();
            """, {
                **r,
                "payload": Jsonb(r.get("payload") or {}),
                "filled": filled,
                "win": None if pnl is None else bool(pnl > 0),
                "outcome_class": outcome,
            })
            saved += 1

    conn.commit()
    return saved


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None)
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()
    trade_date = date.fromisoformat(args.date) if args.date else None

    with psycopg.connect(database_url) as conn:
        if args.migrate:
            migrate(conn)

        saved = build(conn, trade_date=trade_date) if args.save else 0

    print(
        f"SIGNAL_QUALITY_AUDIT_V1_OK date={args.date or '*'} saved={saved}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
