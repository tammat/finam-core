from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


DDL = """
CREATE TABLE IF NOT EXISTS analytics_strategy_trades_v2 (
    id bigserial PRIMARY KEY,
    symbol text NOT NULL,
    strategy text NOT NULL,
    timeframe text NOT NULL,
    origin text NOT NULL,
    side text NOT NULL,
    entry_trade_id bigint NOT NULL,
    exit_trade_id bigint NOT NULL,
    entry_ts timestamptz NOT NULL,
    exit_ts timestamptz NOT NULL,
    entry_price double precision NOT NULL,
    exit_price double precision NOT NULL,
    qty double precision NOT NULL,
    gross_pnl double precision NOT NULL,
    commission double precision NOT NULL DEFAULT 0,
    net_pnl double precision NOT NULL,
    signal_id text,
    holding_seconds double precision NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(entry_trade_id, exit_trade_id)
);

CREATE INDEX IF NOT EXISTS idx_ast_v2_symbol_strategy
ON analytics_strategy_trades_v2(symbol, strategy, timeframe);

CREATE INDEX IF NOT EXISTS idx_ast_v2_exit_ts
ON analytics_strategy_trades_v2(exit_ts DESC);
"""


LOAD_SQL = """
SELECT
    id,
    symbol,
    side,
    qty,
    price,
    commission,
    fill_id,
    origin,
    trade_source,
    strategy,
    timeframe,
    payload,
    created_at,
    ts
FROM trades
WHERE is_invalid = false
  AND origin IN ('paper', 'replay_br_pipeline', 'historical_signal_replay')
  AND strategy <> ''
  AND price > 0
  AND qty > 0
  AND created_at >= now() - (%(window_days)s * interval '1 day')
ORDER BY symbol, strategy, timeframe, origin, created_at, id;
"""


SUMMARY_SQL = """
SELECT
    symbol,
    strategy,
    timeframe,
    origin,
    count(*) AS closed_trades,
    round(sum(net_pnl)::numeric, 6) AS net_pnl,
    round(avg(net_pnl)::numeric, 6) AS avg_net_pnl,
    round(
        (
            sum(net_pnl) FILTER (WHERE net_pnl > 0)
            /
            nullif(abs(sum(net_pnl) FILTER (WHERE net_pnl < 0)), 0)
        )::numeric,
        6
    ) AS profit_factor,
    round(
        (
            count(*) FILTER (WHERE net_pnl > 0)::numeric
            / nullif(count(*), 0)
        ),
        6
    ) AS winrate,
    min(entry_ts) AS first_entry,
    max(exit_ts) AS last_exit
FROM analytics_strategy_trades_v2
GROUP BY symbol, strategy, timeframe, origin
ORDER BY closed_trades DESC, net_pnl DESC;
"""


@dataclass
class OpenLeg:
    trade_id: int
    ts: Any
    price: float
    qty: float
    commission: float
    signal_id: str | None


def norm_side(side: str) -> str:
    s = str(side or "").upper()
    if s in {"BUY", "LONG"}:
        return "BUY"
    if s in {"SELL", "SHORT"}:
        return "SELL"
    return s


def payload_signal_id(payload: Any) -> str | None:
    if isinstance(payload, dict):
        value = payload.get("signal_id")
        return str(value) if value is not None else None
    return None


def pair_group(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    long_stack: list[OpenLeg] = []
    short_stack: list[OpenLeg] = []
    result: list[dict[str, Any]] = []

    for r in rows:
        side = norm_side(r["side"])
        qty_left = float(r["qty"])
        price = float(r["price"])
        commission = float(r.get("commission") or 0.0)
        signal_id = payload_signal_id(r.get("payload"))

        if side == "BUY":
            # Русский комментарий:
            # BUY сначала закрывает открытые SHORT, остаток открывает LONG.
            while qty_left > 1e-12 and short_stack:
                leg = short_stack[0]
                q = min(qty_left, leg.qty)
                gross = (leg.price - price) * q
                comm = commission * (q / float(r["qty"])) + leg.commission * (q / leg.qty)
                result.append({
                    "symbol": r["symbol"],
                    "strategy": r["strategy"],
                    "timeframe": r["timeframe"],
                    "origin": r["origin"],
                    "side": "SHORT",
                    "entry_trade_id": leg.trade_id,
                    "exit_trade_id": r["id"],
                    "entry_ts": leg.ts,
                    "exit_ts": r["created_at"],
                    "entry_price": leg.price,
                    "exit_price": price,
                    "qty": q,
                    "gross_pnl": gross,
                    "commission": comm,
                    "net_pnl": gross - comm,
                    "signal_id": leg.signal_id or signal_id,
                    "holding_seconds": (r["created_at"] - leg.ts).total_seconds(),
                })
                leg.qty -= q
                qty_left -= q
                if leg.qty <= 1e-12:
                    short_stack.pop(0)

            if qty_left > 1e-12:
                long_stack.append(OpenLeg(r["id"], r["created_at"], price, qty_left, commission, signal_id))

        elif side == "SELL":
            # Русский комментарий:
            # SELL сначала закрывает открытые LONG, остаток открывает SHORT.
            while qty_left > 1e-12 and long_stack:
                leg = long_stack[0]
                q = min(qty_left, leg.qty)
                gross = (price - leg.price) * q
                comm = commission * (q / float(r["qty"])) + leg.commission * (q / leg.qty)
                result.append({
                    "symbol": r["symbol"],
                    "strategy": r["strategy"],
                    "timeframe": r["timeframe"],
                    "origin": r["origin"],
                    "side": "LONG",
                    "entry_trade_id": leg.trade_id,
                    "exit_trade_id": r["id"],
                    "entry_ts": leg.ts,
                    "exit_ts": r["created_at"],
                    "entry_price": leg.price,
                    "exit_price": price,
                    "qty": q,
                    "gross_pnl": gross,
                    "commission": comm,
                    "net_pnl": gross - comm,
                    "signal_id": leg.signal_id or signal_id,
                    "holding_seconds": (r["created_at"] - leg.ts).total_seconds(),
                })
                leg.qty -= q
                qty_left -= q
                if leg.qty <= 1e-12:
                    long_stack.pop(0)

            if qty_left > 1e-12:
                short_stack.append(OpenLeg(r["id"], r["created_at"], price, qty_left, commission, signal_id))

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-days", type=int, default=365)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    print("TRADE_PAIRING_V2_START", flush=True)

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(DDL)

            if args.reset:
                cur.execute("TRUNCATE analytics_strategy_trades_v2;")

            cur.execute(LOAD_SQL, {"window_days": args.window_days})
            rows = [dict(x) for x in cur.fetchall()]

            groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
            for row in rows:
                key = (row["symbol"], row["strategy"], row["timeframe"], row["origin"])
                groups.setdefault(key, []).append(row)

            paired: list[dict[str, Any]] = []
            for group_rows in groups.values():
                paired.extend(pair_group(group_rows))

            insert_sql = """
            INSERT INTO analytics_strategy_trades_v2 (
                symbol, strategy, timeframe, origin, side,
                entry_trade_id, exit_trade_id,
                entry_ts, exit_ts,
                entry_price, exit_price, qty,
                gross_pnl, commission, net_pnl,
                signal_id, holding_seconds
            )
            VALUES (
                %(symbol)s, %(strategy)s, %(timeframe)s, %(origin)s, %(side)s,
                %(entry_trade_id)s, %(exit_trade_id)s,
                %(entry_ts)s, %(exit_ts)s,
                %(entry_price)s, %(exit_price)s, %(qty)s,
                %(gross_pnl)s, %(commission)s, %(net_pnl)s,
                %(signal_id)s, %(holding_seconds)s
            )
            ON CONFLICT (entry_trade_id, exit_trade_id) DO NOTHING;
            """

            inserted = 0
            for item in paired:
                cur.execute(insert_sql, item)
                inserted += cur.rowcount

            cur.execute(SUMMARY_SQL)
            summary = [dict(x) for x in cur.fetchall()]

        conn.commit()

    print(f"TRADE_PAIRING_V2_LOADED source_rows={len(rows)} paired_rows={len(paired)} inserted_rows={inserted}", flush=True)
    for row in summary:
        print(" ".join(["TRADE_PAIRING_V2_SUMMARY"] + [f"{k}={v}" for k, v in row.items()]), flush=True)

    print("TRADE_PAIRING_V2_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
