#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SQL_TRADES = """
select
    coalesce(origin,'NULL') as origin,
    coalesce(trade_source,'NULL') as trade_source,
    count(*) rows
from trades
group by 1,2
order by rows desc;
"""

SQL_V3_CHAINS = """
select
    symbol,
    strategy,
    timeframe,
    trade_source,
    count(*) chains
from closed_trade_chains_v3
group by 1,2,3,4
order by chains desc;
"""

SQL_ATTR = """
select
    symbol,
    strategy,
    timeframe,
    trade_source,
    attribution_quality,
    count(*) rows
from trade_attribution_v3
group by 1,2,3,4,5
order by rows desc;
"""

def main() -> int:
    print("=== SOURCE SEPARATION AUDIT V1 ===")
    print("mode=architecture_audit")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            cur.execute(SQL_TRADES)
            trades = cur.fetchall()

            cur.execute(SQL_V3_CHAINS)
            chains = cur.fetchall()

            cur.execute(SQL_ATTR)
            attrs = cur.fetchall()

    print("SOURCE_LAYER=TRADES")

    for r in trades:
        print(
            "SOURCE_TRADES_ROW "
            f"origin={r['origin']} "
            f"trade_source={r['trade_source']} "
            f"rows={r['rows']}"
        )

    print("SOURCE_LAYER=CLOSED_TRADE_CHAINS_V3")

    for r in chains:
        print(
            "SOURCE_CHAINS_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"trade_source={r['trade_source']} "
            f"chains={r['chains']}"
        )

    print("SOURCE_LAYER=TRADE_ATTRIBUTION_V3")

    for r in attrs:
        print(
            "SOURCE_ATTR_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"trade_source={r['trade_source']} "
            f"quality={r['attribution_quality']} "
            f"rows={r['rows']}"
        )

    print("SOURCE_SEPARATION_AUDIT_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
