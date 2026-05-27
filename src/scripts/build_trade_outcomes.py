#!/usr/bin/env python3
import argparse
import os

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from finam_core.analytics.trade_outcome_engine import TradeFill, TradeOutcomeEngine
from finam_core.analytics.regime_attribution import derive_regime_label, is_known_regime



def _enrich_regime_payload(payload: dict) -> dict:
    """Русский комментарий: v1.2 разворачивает вложенный payload и сохраняет regime attribution в outcomes."""
    base = dict(payload or {})
    nested = base.get("payload") if isinstance(base.get("payload"), dict) else {}

    enriched = dict(base)
    for key, value in nested.items():
        if key not in enriched or enriched.get(key) in (None, "", {}, []):
            enriched[key] = value

    current = enriched.get("regime") or enriched.get("regime_label")
    if not is_known_regime(current):
        derived = derive_regime_label(enriched)
        enriched["regime"] = derived
        enriched["regime_label"] = derived

    if "payload" in enriched:
        enriched["_nested_payload_unwrapped"] = True

    return enriched


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--trade-source", default="paper")
    parser.add_argument("--from-id", type=int, default=0)
    parser.add_argument("--to-id", type=int, default=0)
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set")

    select_sql = """
    select
        id,
        symbol,
        side,
        qty,
        price,
        coalesce(commission, 0) as commission,
        coalesce(ts, created_at) as ts,
        fill_id,
        trade_source,
        strategy,
        timeframe,
        continuous_symbol,
        payload
    from trades
    where symbol = %(symbol)s
      and trade_source = %(trade_source)s
      and coalesce(is_invalid, false) = false
      and (%(from_id)s = 0 or id >= %(from_id)s)
      and (%(to_id)s = 0 or id <= %(to_id)s)
    order by coalesce(ts, created_at), id;
    """

    insert_sql = """
    insert into trade_outcomes (
        entry_trade_id, exit_trade_id,
        entry_fill_id, exit_fill_id,
        symbol, continuous_symbol, strategy, timeframe, trade_source,
        entry_side, exit_side, qty,
        entry_price, exit_price,
        gross_pnl, commission, net_pnl,
        entry_ts, exit_ts, holding_seconds,
        run_id, raw_json
    )
    values (
        %(entry_trade_id)s, %(exit_trade_id)s,
        %(entry_fill_id)s, %(exit_fill_id)s,
        %(symbol)s, %(continuous_symbol)s, %(strategy)s, %(timeframe)s, %(trade_source)s,
        %(entry_side)s, %(exit_side)s, %(qty)s,
        %(entry_price)s, %(exit_price)s,
        %(gross_pnl)s, %(commission)s, %(net_pnl)s,
        %(entry_ts)s, %(exit_ts)s, %(holding_seconds)s,
        %(run_id)s, %(raw_json)s
    )
    on conflict (entry_trade_id, exit_trade_id)
    do update set
        continuous_symbol = excluded.continuous_symbol,
        strategy = excluded.strategy,
        timeframe = excluded.timeframe,
        gross_pnl = excluded.gross_pnl,
        commission = excluded.commission,
        net_pnl = excluded.net_pnl,
        holding_seconds = excluded.holding_seconds,
        raw_json = excluded.raw_json;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                select_sql,
                {
                    "symbol": args.symbol,
                    "trade_source": args.trade_source,
                    "from_id": args.from_id,
                    "to_id": args.to_id,
                },
            )
            rows = cur.fetchall()

        fills = [
            TradeFill(
                id=int(r["id"]),
                symbol=str(r["symbol"]),
                side=str(r["side"]),
                qty=float(r["qty"] or 0.0),
                price=float(r["price"] or 0.0),
                commission=float(r["commission"] or 0.0),
                ts=r["ts"],
                fill_id=r["fill_id"],
                trade_source=str(r["trade_source"]),
                strategy=r["strategy"],
                timeframe=r["timeframe"],
                continuous_symbol=r["continuous_symbol"],
                payload=_enrich_regime_payload(r["payload"] if isinstance(r["payload"], dict) else {}),
            )
            for r in rows
        ]

        outcomes = TradeOutcomeEngine().build(fills)

        with conn.cursor() as cur:
            for o in outcomes:
                cur.execute(
                    insert_sql,
                    {
                        "entry_trade_id": o.entry_trade_id,
                        "exit_trade_id": o.exit_trade_id,
                        "entry_fill_id": o.entry_fill_id,
                        "exit_fill_id": o.exit_fill_id,
                        "symbol": o.symbol,
                        "continuous_symbol": o.continuous_symbol,
                        "strategy": o.strategy,
                        "timeframe": o.timeframe,
                        "trade_source": o.trade_source,
                        "entry_side": o.entry_side,
                        "exit_side": o.exit_side,
                        "qty": o.qty,
                        "entry_price": o.entry_price,
                        "exit_price": o.exit_price,
                        "gross_pnl": o.gross_pnl,
                        "commission": o.commission,
                        "net_pnl": o.net_pnl,
                        "entry_ts": o.entry_ts,
                        "exit_ts": o.exit_ts,
                        "holding_seconds": o.holding_seconds,
                        "run_id": o.run_id,
                        "raw_json": Jsonb(o.raw_json),
                    },
                )

        conn.commit()

    net = sum(o.net_pnl for o in outcomes)
    wins = sum(1 for o in outcomes if o.net_pnl > 0)
    losses = sum(1 for o in outcomes if o.net_pnl < 0)

    print(
        "TRADE_OUTCOMES_BUILT",
        f"symbol={args.symbol}",
        f"trade_source={args.trade_source}",
        f"fills={len(fills)}",
        f"outcomes={len(outcomes)}",
        f"wins={wins}",
        f"losses={losses}",
        f"net_pnl={net:.4f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
