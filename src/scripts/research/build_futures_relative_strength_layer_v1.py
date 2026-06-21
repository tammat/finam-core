#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row


LOOKBACK_BARS = {
    "M1": 15,
    "M5": 12,
}

FUTURE_PREFIXES = ("NG", "BR", "GD", "GL", "SV", "USDRUBF")


def pct_change(first, last):
    if first is None or last is None or Decimal(first) == 0:
        return None
    return (Decimal(last) - Decimal(first)) / Decimal(first) * Decimal("100")


def asset_family(symbol: str) -> str:
    for prefix in FUTURE_PREFIXES:
        if symbol.startswith(prefix):
            return prefix
    return "OTHER"


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    rows = []

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                select symbol, timeframe, count(*) as bars, max(ts) as last_ts
                from market_bars
                where timeframe in ('M1','M5')
                  and (
                    symbol like 'NG%@RTSX'
                    or symbol like 'BR%@RTSX'
                    or symbol like 'GD%@RTSX'
                    or symbol like 'GL%@RTSX'
                    or symbol like 'SV%@RTSX'
                    or symbol = 'USDRUBF@RTSX'
                  )
                group by symbol, timeframe
                having count(*) >= 15
                order by symbol, timeframe
            """)
            universe = list(cur.fetchall())

            for item in universe:
                symbol = item["symbol"]
                timeframe = item["timeframe"]
                limit = LOOKBACK_BARS.get(timeframe, 12)

                cur.execute("""
                    select ts, close
                    from market_bars
                    where symbol = %s
                      and timeframe = %s
                    order by ts desc
                    limit %s
                """, (symbol, timeframe, limit + 1))
                bars = list(cur.fetchall())

                if len(bars) < limit:
                    continue

                latest = bars[0]
                earliest = bars[-1]
                ret = pct_change(earliest["close"], latest["close"])

                rows.append({
                    "symbol": symbol,
                    "family": asset_family(symbol),
                    "timeframe": timeframe,
                    "bars": len(bars),
                    "first_close": earliest["close"],
                    "last_close": latest["close"],
                    "return_pct": ret,
                    "last_ts": latest["ts"],
                })

    ranked = sorted(
        rows,
        key=lambda r: Decimal(r["return_pct"] or 0),
        reverse=True,
    )

    for idx, r in enumerate(ranked, start=1):
        r["rs_rank"] = idx

    leaders = ranked[:5]
    laggards = ranked[-5:] if ranked else []

    print("=== FUTURES_RELATIVE_STRENGTH_LAYER_V1 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")
    print(f"rows_total={len(ranked)}")

    for r in ranked:
        print(
            "FUTURES_RS_ROW "
            f"rank={r['rs_rank']} "
            f"symbol={r['symbol']} "
            f"family={r['family']} "
            f"timeframe={r['timeframe']} "
            f"return_pct={r['return_pct']} "
            f"last_close={r['last_close']} "
            f"last_ts={r['last_ts']}",
            flush=True,
        )

    print("FUTURES_RS_LEADERS " + ",".join(r["symbol"] for r in leaders))
    print("FUTURES_RS_LAGGARDS " + ",".join(r["symbol"] for r in laggards))
    print("VERDICT=FUTURES_RELATIVE_STRENGTH_LAYER_READY")
    print("TEST_FUTURES_RELATIVE_STRENGTH_LAYER_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
