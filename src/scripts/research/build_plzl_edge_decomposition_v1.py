#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SYMBOL = "PLZL@MISX"
STRATEGIES = ("MOEX_SIMPLE_MOMENTUM", "MOEX_MEAN_REVERSION_V1")

SQL = """
select
    symbol,
    strategy,
    timeframe,
    date_trunc('month', created_at)::date as month,
    count(*) as trades,
    sum(pnl)::float as pnl,
    avg(pnl)::float as expectancy,
    sum(case when pnl > 0 then 1 else 0 end)::float / nullif(count(*),0) as winrate,
    sum(case when pnl > 0 then pnl else 0 end)::float as gross_profit,
    abs(sum(case when pnl < 0 then pnl else 0 end))::float as gross_loss
from trade_attribution_v2
where symbol=%s
  and strategy = any(%s)
  and timeframe='D1'
  and trade_source='paper'
group by symbol, strategy, timeframe, date_trunc('month', created_at)::date
order by strategy, month;
"""

def pf(gp: float, gl: float) -> float:
    if gl > 0:
        return gp / gl
    return 999.0 if gp > 0 else 0.0

def main() -> int:
    print("=== PLZL EDGE DECOMPOSITION V1 ===", flush=True)
    print("mode=research_only", flush=True)
    print("execution_enabled=0", flush=True)

    rows = []
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOL, list(STRATEGIES)))
            rows = cur.fetchall()

    total_rows = 0
    weak_months = 0

    for r in rows:
        total_rows += 1
        profit_factor = pf(float(r["gross_profit"] or 0), float(r["gross_loss"] or 0))
        if float(r["expectancy"] or 0) <= 0:
            weak_months += 1

        print(
            "PLZL_EDGE_MONTH "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"month={r['month']} "
            f"trades={r['trades']} "
            f"pnl={float(r['pnl'] or 0):.4f} "
            f"expectancy={float(r['expectancy'] or 0):.4f} "
            f"winrate={float(r['winrate'] or 0):.4f} "
            f"profit_factor={profit_factor:.4f}",
            flush=True,
        )

    print(
        "PLZL_EDGE_DECOMPOSITION_SUMMARY "
        f"rows={total_rows} "
        f"weak_months={weak_months} "
        "runtime_allow=0 "
        "execution_enabled=0",
        flush=True,
    )

    print("PLZL_EDGE_DECOMPOSITION_V1_OK", flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
