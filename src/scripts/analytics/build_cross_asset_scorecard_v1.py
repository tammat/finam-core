#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

ASSET_PATTERNS = {
    "USD": ["USDRUBF@RTSX", "SI%", "%USD%"],
    "GOLD": ["%GOLD%", "GD%", "GLD%", "GDU%", "GLDRUB%"],
    "BTC": ["%BTC%", "%BITCOIN%"],
}

SQL = """
WITH matched AS (
    SELECT
        %(asset)s::text AS asset,
        symbol,
        net_pnl,
        COALESCE(exit_ts, closed_at, created_at) AS ts
    FROM closed_trades
    WHERE
        symbol = ANY(%(exact_symbols)s)
        OR symbol ILIKE ANY(%(like_patterns)s)
)
SELECT
    asset,
    symbol,
    COUNT(*) AS trades,
    ROUND(COALESCE(SUM(net_pnl),0)::numeric,6) AS net_pnl,
    ROUND(COALESCE(AVG(net_pnl),0)::numeric,6) AS expectancy,
    ROUND(
        100.0 * SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*),0),
        2
    ) AS winrate,
    ROUND(COALESCE(SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END),0)::numeric,6) AS gross_profit,
    ROUND(COALESCE(ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END)),0)::numeric,6) AS gross_loss,
    MAX(ts) AS last_trade_ts
FROM matched
GROUP BY asset, symbol
ORDER BY asset, net_pnl DESC;
"""

def split_patterns(patterns: list[str]) -> tuple[list[str], list[str]]:
    exact = []
    like = []
    for p in patterns:
        if "%" in p or "_" in p:
            like.append(p)
        else:
            exact.append(p)
    return exact, like

def profit_factor(gp, gl):
    gp_f = float(gp or 0)
    gl_f = float(gl or 0)
    if gl_f <= 0:
        return None
    return round(gp_f / gl_f, 4)

def status(trades: int, expectancy: float, pf):
    if trades < 20:
        return "NO_DATA"
    if expectancy > 0 and pf is not None and pf > 1.2:
        return "PROMOTE"
    if expectancy < 0:
        return "DISABLE"
    return "WATCH"

def main() -> None:
    print("=== CROSS ASSET SCORECARD V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("assets=USD,GOLD,BTC")
    print()

    all_rows = []

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for asset, patterns in ASSET_PATTERNS.items():
                exact, like = split_patterns(patterns)
                cur.execute(
                    SQL,
                    {
                        "asset": asset,
                        "exact_symbols": exact or ["__NO_EXACT_MATCH__"],
                        "like_patterns": like or ["__NO_LIKE_MATCH__"],
                    },
                )
                all_rows.extend([dict(r) for r in cur.fetchall()])

    print("ASSET_ROWS")

    if not all_rows:
        print("NONE")

    seen_assets = set()

    for r in all_rows:
        seen_assets.add(r["asset"])
        trades = int(r["trades"])
        expectancy = float(r["expectancy"] or 0)
        pf = profit_factor(r["gross_profit"], r["gross_loss"])
        st = status(trades, expectancy, pf)

        print(
            "ASSET_ROW "
            f"asset={r['asset']} "
            f"symbol={r['symbol']} "
            f"trades={trades} "
            f"net_pnl={r['net_pnl']} "
            f"expectancy={r['expectancy']} "
            f"winrate={r['winrate']} "
            f"profit_factor={pf} "
            f"status={st} "
            f"last_trade_ts={r['last_trade_ts']}"
        )

    for asset in ASSET_PATTERNS:
        if asset not in seen_assets:
            print(
                "ASSET_ROW "
                f"asset={asset} "
                "symbol=NONE "
                "trades=0 "
                "net_pnl=0 "
                "expectancy=0 "
                "winrate=None "
                "profit_factor=None "
                "status=NO_DATA "
                "last_trade_ts=None"
            )

    print()
    print("VERDICT=CROSS_ASSET_SCORECARD_RECORDED")
    print("CROSS_ASSET_SCORECARD_V1_OK")

if __name__ == "__main__":
    main()
