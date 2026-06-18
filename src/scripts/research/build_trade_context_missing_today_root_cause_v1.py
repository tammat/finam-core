#!/usr/bin/env python3
from __future__ import annotations

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor


BAD_ROWS_SQL = """
select
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
    continuous_symbol,
    payload,
    created_at,
    ts
from trades
where created_at::date = current_date
  and (
        strategy is null or btrim(strategy) = ''
     or timeframe is null or btrim(timeframe) = ''
     or continuous_symbol is null or btrim(continuous_symbol) = ''
  )
order by created_at, id;
"""


SUMMARY_SQL = """
select
    origin,
    trade_source,
    symbol,
    count(*) as bad_rows,
    min(created_at) as first_bad_trade,
    max(created_at) as last_bad_trade
from trades
where created_at::date = current_date
  and (
        strategy is null or btrim(strategy) = ''
     or timeframe is null or btrim(timeframe) = ''
     or continuous_symbol is null or btrim(continuous_symbol) = ''
  )
group by origin, trade_source, symbol
order by bad_rows desc, origin, trade_source, symbol;
"""


def payload_get(payload: object, key: str) -> str:
    if not isinstance(payload, dict):
        return ""

    value = payload.get(key)
    if value is not None:
        return str(value)

    nested = payload.get("payload")
    if isinstance(nested, dict):
        value = nested.get(key)
        if value is not None:
            return str(value)

    return ""


def payload_keys(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""

    keys = sorted(str(k) for k in payload.keys())
    return ",".join(keys)


def main() -> int:
    dsn = os.getenv("DATABASE_URL", "dbname=finam_core user=postgres")

    print("=== TRADE CONTEXT MISSING TODAY ROOT CAUSE V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(SUMMARY_SQL)
            summary_rows = cur.fetchall()

            print()
            print("MISSING_CONTEXT_TODAY_SUMMARY_ROWS")
            for row in summary_rows:
                print(
                    "MISSING_CONTEXT_SUMMARY_ROW "
                    f"origin={row['origin']} "
                    f"trade_source={row['trade_source']} "
                    f"symbol={row['symbol']} "
                    f"bad_rows={row['bad_rows']} "
                    f"first_bad_trade={row['first_bad_trade']} "
                    f"last_bad_trade={row['last_bad_trade']}"
                )

            cur.execute(BAD_ROWS_SQL)
            rows = cur.fetchall()

            print()
            print("MISSING_CONTEXT_TODAY_ROWS")
            for row in rows:
                payload = row["payload"]

                print(
                    "MISSING_CONTEXT_ROW "
                    f"id={row['id']} "
                    f"symbol={row['symbol']} "
                    f"side={row['side']} "
                    f"qty={row['qty']} "
                    f"price={row['price']} "
                    f"fill_id={row['fill_id']} "
                    f"origin={row['origin']} "
                    f"trade_source={row['trade_source']} "
                    f"strategy={row['strategy']} "
                    f"timeframe={row['timeframe']} "
                    f"continuous_symbol={row['continuous_symbol']} "
                    f"payload_strategy={payload_get(payload, 'strategy')} "
                    f"payload_timeframe={payload_get(payload, 'timeframe')} "
                    f"payload_continuous_symbol={payload_get(payload, 'continuous_symbol')} "
                    f"payload_reason={payload_get(payload, 'reason')} "
                    f"payload_execution_type={payload_get(payload, 'execution_type')} "
                    f"payload_keys={payload_keys(payload)} "
                    f"created_at={row['created_at']} "
                    f"ts={row['ts']}"
                )

    print()
    print(f"bad_rows={len(rows)}")

    if len(rows) == 0:
        print("VERDICT=TRADE_CONTEXT_MISSING_TODAY_NONE")
    else:
        print("VERDICT=TRADE_CONTEXT_MISSING_TODAY_ROOT_CAUSE_READY")

    print("TRADE_CONTEXT_MISSING_TODAY_ROOT_CAUSE_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
