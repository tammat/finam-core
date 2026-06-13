#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SYMBOL = "USDRUBF@RTSX"
STRATEGY = "usdrub_shadow_signal_research_v1"
EXIT_BARS = 10
LOSS_CAP = -2.0

SQL = """
WITH signals AS (
    SELECT
        signal_ts,
        side,
        entry_price::numeric AS entry_price,
        ROW_NUMBER() OVER (ORDER BY signal_ts) AS rn
    FROM usdrub_shadow_signals
    WHERE symbol=%s
      AND strategy=%s
      AND timeframe='M5'
),
scored AS (
    SELECT
        s.signal_ts,
        s.side,
        s.entry_price,
        e.signal_ts AS exit_ts,
        e.entry_price AS exit_price,
        CASE
            WHEN e.entry_price IS NULL THEN NULL
            WHEN s.side='BUY' THEN e.entry_price - s.entry_price
            WHEN s.side='SELL' THEN s.entry_price - e.entry_price
            ELSE NULL
        END AS pnl
    FROM signals s
    LEFT JOIN signals e ON e.rn = s.rn + %s
)
SELECT *
FROM scored
WHERE pnl IS NOT NULL;
"""

def calc_metrics(pnls: list[float]) -> dict:
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]
    trades = len(pnls)
    net = round(sum(pnls), 6)
    expectancy = round(net / trades, 6) if trades else None
    winrate = round(len(wins) / trades * 100, 2) if trades else None
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    pf = round(gross_profit / gross_loss, 4) if gross_loss else None
    return {
        "trades": trades,
        "wins": len(wins),
        "losses": len(losses),
        "net_pnl": net,
        "expectancy": expectancy,
        "winrate": winrate,
        "profit_factor": pf,
    }

def main() -> int:
    print("=== USDRUB LOSS TAIL FILTER V1 ===")
    print("mode=research_filter")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print(f"exit_bars={EXIT_BARS}")
    print(f"loss_cap={LOSS_CAP}")
    print()

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOL, STRATEGY, EXIT_BARS))
            rows = cur.fetchall()

    raw_pnls = [float(r["pnl"]) for r in rows]
    capped_pnls = [max(float(r["pnl"]), LOSS_CAP) for r in rows]
    blocked_tail = [x for x in raw_pnls if x < LOSS_CAP]

    raw = calc_metrics(raw_pnls)
    capped = calc_metrics(capped_pnls)

    improvement = round(capped["net_pnl"] - raw["net_pnl"], 6)

    if capped["expectancy"] is not None and capped["expectancy"] > 0 and (capped["profit_factor"] or 0) >= 1.2:
        verdict = "USDRUB_LOSS_TAIL_FILTER_USEFUL"
    else:
        verdict = "USDRUB_LOSS_TAIL_FILTER_NOT_ENOUGH"

    print(
        "RAW_ROW "
        f"trades={raw['trades']} "
        f"wins={raw['wins']} "
        f"losses={raw['losses']} "
        f"winrate={raw['winrate']} "
        f"net_pnl={raw['net_pnl']} "
        f"expectancy={raw['expectancy']} "
        f"profit_factor={raw['profit_factor']}"
    )

    print(
        "FILTER_ROW "
        f"loss_cap={LOSS_CAP} "
        f"tail_trades={len(blocked_tail)} "
        f"capped_trades={capped['trades']} "
        f"wins={capped['wins']} "
        f"losses={capped['losses']} "
        f"winrate={capped['winrate']} "
        f"net_pnl={capped['net_pnl']} "
        f"expectancy={capped['expectancy']} "
        f"profit_factor={capped['profit_factor']} "
        f"pnl_improvement={improvement}"
    )

    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print(f"VERDICT={verdict}")
    print("USDRUB_LOSS_TAIL_FILTER_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
