#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

SQL = """
WITH normalized AS (
    SELECT
        CASE
            WHEN root_symbol IS NOT NULL AND root_symbol <> '' THEN root_symbol
            WHEN symbol ~ '^BR[A-Z][0-9]@RTSX$' THEN 'BR'
            WHEN symbol ~ '^NG[A-Z][0-9]@RTSX$' THEN 'NG'
            WHEN symbol LIKE 'USDRUB%' THEN 'USDRUB'
            ELSE split_part(symbol, '@', 1)
        END AS normalized_root,
        symbol,
        net_pnl,
        COALESCE(exit_ts, closed_at, created_at) AS trade_ts
    FROM closed_trades
)
SELECT
    normalized_root AS root,
    symbol,
    COUNT(*) AS trades,
    ROUND(SUM(net_pnl)::numeric,6) AS net_pnl,
    ROUND(AVG(net_pnl)::numeric,6) AS expectancy,
    ROUND(
        100.0 *
        SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*),0),
        2
    ) AS winrate,
    ROUND(
        SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END)::numeric,
        6
    ) AS gross_profit,
    ROUND(
        ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END))::numeric,
        6
    ) AS gross_loss,
    MAX(trade_ts) AS last_trade_ts
FROM normalized
GROUP BY normalized_root, symbol
ORDER BY net_pnl DESC;
"""

ROOT_SQL = """
WITH normalized AS (
    SELECT
        CASE
            WHEN root_symbol IS NOT NULL AND root_symbol <> '' THEN root_symbol
            WHEN symbol ~ '^BR[A-Z][0-9]@RTSX$' THEN 'BR'
            WHEN symbol ~ '^NG[A-Z][0-9]@RTSX$' THEN 'NG'
            WHEN symbol LIKE 'USDRUB%' THEN 'USDRUB'
            ELSE split_part(symbol, '@', 1)
        END AS normalized_root,
        net_pnl,
        COALESCE(exit_ts, closed_at, created_at) AS trade_ts
    FROM closed_trades
)
SELECT
    normalized_root AS root,
    COUNT(*) AS trades,
    ROUND(SUM(net_pnl)::numeric,6) AS net_pnl,
    ROUND(AVG(net_pnl)::numeric,6) AS expectancy,
    ROUND(
        100.0 *
        SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*),0),
        2
    ) AS winrate,
    ROUND(
        SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END)::numeric,
        6
    ) AS gross_profit,
    ROUND(
        ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END))::numeric,
        6
    ) AS gross_loss,
    MAX(trade_ts) AS last_trade_ts
FROM normalized
GROUP BY normalized_root
ORDER BY net_pnl DESC;
"""

def pf(gross_profit, gross_loss):
    gp = float(gross_profit or 0)
    gl = float(gross_loss or 0)
    if gl <= 0:
        return None
    return round(gp / gl, 4)

def status(trades: int, expectancy: float, profit_factor):
    if trades < 20:
        return "NO_DATA"
    if expectancy > 0 and profit_factor is not None and profit_factor > 1.20:
        return "PROMOTE"
    if expectancy < 0:
        return "DISABLE"
    return "WATCH"

def emit_row(prefix: str, r: dict, root_key: str = "root"):
    trades = int(r["trades"])
    expectancy = float(r["expectancy"] or 0)
    profit_factor = pf(r["gross_profit"], r["gross_loss"])
    st = status(trades, expectancy, profit_factor)

    fields = [
        f"root={r[root_key]}",
    ]
    if "symbol" in r:
        fields.append(f"symbol={r['symbol']}")
    fields.extend([
        f"trades={trades}",
        f"net_pnl={r['net_pnl']}",
        f"expectancy={r['expectancy']}",
        f"winrate={r['winrate']}",
        f"profit_factor={profit_factor}",
        f"status={st}",
        f"last_trade_ts={r['last_trade_ts']}",
    ])
    print(prefix + " " + " ".join(fields))

def main() -> None:
    print("=== ALL SYMBOLS RUNTIME SCORECARD V1.1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("normalization=derived_root_symbol")
    print()

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)
            symbol_rows = cur.fetchall()

            cur.execute(ROOT_SQL)
            root_rows = cur.fetchall()

    print("ROOT_SCORECARD")
    for r in root_rows:
        emit_row("ROOT_ROW", r)
    print()

    print("SYMBOL_SCORECARD")
    for r in symbol_rows:
        emit_row("SYMBOL_ROW", r)
    print()

    print(f"ROOT_ROWS={len(root_rows)}")
    print(f"SYMBOL_ROWS={len(symbol_rows)}")
    print("VERDICT=ALL_SYMBOLS_RUNTIME_SCORECARD_NORMALIZED")
    print("ALL_SYMBOLS_RUNTIME_SCORECARD_V1_1_OK")

if __name__ == "__main__":
    main()
