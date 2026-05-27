from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from typing import Any

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


@dataclass
class PositionState:
    qty: float = 0.0
    avg_price: float = 0.0


def calculate_trade_pnl(state: PositionState, side: str, qty: float, price: float) -> float:
    # Русский комментарий:
    # Позиционный расчет P&L: сначала закрываем существующую позицию,
    # затем при необходимости открываем новую в противоположную сторону.
    pnl = 0.0
    signed_qty = qty if side == "BUY" else -qty

    if state.qty == 0:
        state.qty = signed_qty
        state.avg_price = price
        return 0.0

    same_direction = (state.qty > 0 and signed_qty > 0) or (state.qty < 0 and signed_qty < 0)

    if same_direction:
        total_abs_qty = abs(state.qty) + qty
        state.avg_price = ((abs(state.qty) * state.avg_price) + (qty * price)) / total_abs_qty
        state.qty += signed_qty
        return 0.0

    close_qty = min(abs(state.qty), qty)

    if state.qty > 0:
        pnl += close_qty * (price - state.avg_price)
    else:
        pnl += close_qty * (state.avg_price - price)

    remaining_qty = qty - close_qty

    if remaining_qty == 0:
        state.qty += signed_qty
        if abs(state.qty) < 1e-12:
            state.qty = 0.0
            state.avg_price = 0.0
        return pnl

    # Переворот позиции.
    state.qty = remaining_qty if side == "BUY" else -remaining_qty
    state.avg_price = price
    return pnl


def migrate(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS analytics_intraday_pnl (
                id bigserial PRIMARY KEY,
                trade_date date NOT NULL,
                trade_id bigint NOT NULL,
                ts timestamptz NOT NULL,
                symbol text NOT NULL,
                side text NOT NULL,
                qty double precision NOT NULL,
                price double precision NOT NULL,
                position_qty_after double precision NOT NULL,
                avg_price_after double precision NOT NULL,
                trade_pnl double precision NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                UNIQUE (trade_date, trade_id)
            );
            """
        )
        cur.execute(
            """
            CREATE OR REPLACE VIEW v_intraday_pnl_ru AS
            SELECT
                ts AS "Время",
                trade_date AS "Дата",
                symbol AS "Инструмент",
                side AS "Операция",
                qty AS "Количество",
                price AS "Цена",
                position_qty_after AS "Позиция после",
                avg_price_after AS "Средняя цена после",
                round(trade_pnl::numeric, 6) AS "P&L сделки"
            FROM analytics_intraday_pnl
            ORDER BY ts DESC;
            """
        )
        cur.execute(
            """
            CREATE OR REPLACE VIEW v_last_trade_day_pnl_summary_ru AS
            WITH d AS (
                SELECT max(trade_date) AS trade_date
                FROM analytics_intraday_pnl
            )
            SELECT
                now() AS "Время",
                d.trade_date AS "Дата",
                round(COALESCE(sum(p.trade_pnl), 0)::numeric, 2) AS "P&L",
                count(p.*) AS "Сделок",
                count(DISTINCT p.symbol) AS "Инструментов"
            FROM d
            LEFT JOIN analytics_intraday_pnl p ON p.trade_date = d.trade_date
            GROUP BY d.trade_date;
            """
        )


def load_trades(conn: psycopg.Connection, trade_date: date) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, ts, symbol, upper(side) AS side, qty, price
            FROM trades
            WHERE ts::date = %s
              AND is_invalid = false
            ORDER BY symbol, ts, id
            """,
            (trade_date,),
        )
        return [dict(row) for row in cur.fetchall()]


def save_results(conn: psycopg.Connection, trade_date: date, rows: list[dict[str, Any]]) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM analytics_intraday_pnl WHERE trade_date = %s", (trade_date,))
        for row in rows:
            cur.execute(
                """
                INSERT INTO analytics_intraday_pnl (
                    trade_date, trade_id, ts, symbol, side, qty, price,
                    position_qty_after, avg_price_after, trade_pnl
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    trade_date,
                    row["trade_id"],
                    row["ts"],
                    row["symbol"],
                    row["side"],
                    row["qty"],
                    row["price"],
                    row["position_qty_after"],
                    row["avg_price_after"],
                    row["trade_pnl"],
                ),
            )


def build_for_date(conn: psycopg.Connection, trade_date: date) -> list[dict[str, Any]]:
    states: dict[str, PositionState] = {}
    result: list[dict[str, Any]] = []

    for t in load_trades(conn, trade_date):
        symbol = t["symbol"]
        state = states.setdefault(symbol, PositionState())

        pnl = calculate_trade_pnl(
            state=state,
            side=t["side"],
            qty=float(t["qty"]),
            price=float(t["price"]),
        )

        result.append(
            {
                "trade_id": t["id"],
                "ts": t["ts"],
                "symbol": symbol,
                "side": t["side"],
                "qty": float(t["qty"]),
                "price": float(t["price"]),
                "position_qty_after": state.qty,
                "avg_price_after": state.avg_price,
                "trade_pnl": pnl,
            }
        )

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--migrate", action="store_true")
    args = parser.parse_args()

    trade_date = date.fromisoformat(args.date)
    database_url = build_psycopg_url()

    with psycopg.connect(database_url) as conn:
        if args.migrate:
            migrate(conn)

        rows = build_for_date(conn, trade_date)

        if args.save:
            save_results(conn, trade_date, rows)

        conn.commit()

    total_pnl = sum(r["trade_pnl"] for r in rows)
    print(
        f"INTRADAY_PNL_OK date={trade_date} rows={len(rows)} pnl={total_pnl:.6f}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
