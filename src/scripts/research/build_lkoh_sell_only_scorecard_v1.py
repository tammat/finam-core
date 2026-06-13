#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from decimal import Decimal

import psycopg2
import psycopg2.extras

SYMBOL = "LKOH@MISX"
SOURCE_STRATEGY = "lkoh_shadow_signal_research_v1"
STRATEGY = "lkoh_sell_only_scorecard_v1"
EXIT_BARS = 10

DDL = """
CREATE TABLE IF NOT EXISTS lkoh_sell_only_scorecard (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    source_strategy text NOT NULL,
    strategy text NOT NULL,
    exit_bars integer NOT NULL,
    signals integer NOT NULL,
    closed_trades integer NOT NULL,
    wins integer NOT NULL,
    losses integer NOT NULL,
    winrate numeric,
    net_pnl numeric,
    expectancy numeric,
    profit_factor numeric,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    verdict text NOT NULL,
    raw_json jsonb
);

CREATE INDEX IF NOT EXISTS idx_lkoh_sell_only_scorecard_symbol_created
ON lkoh_sell_only_scorecard(symbol, created_at DESC);
"""

SQL = """
WITH signals AS (
    SELECT
        signal_ts,
        side,
        entry_price::numeric AS entry_price,
        ROW_NUMBER() OVER (ORDER BY signal_ts) AS rn
    FROM lkoh_shadow_signals
    WHERE symbol=%s
      AND strategy=%s
      AND timeframe='M5'
      AND side='SELL'
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
            ELSE s.entry_price - e.entry_price
        END AS pnl
    FROM signals s
    LEFT JOIN signals e ON e.rn = s.rn + %s
)
SELECT *
FROM scored
ORDER BY signal_ts;
"""

INSERT = """
INSERT INTO lkoh_sell_only_scorecard (
    symbol,
    source_strategy,
    strategy,
    exit_bars,
    signals,
    closed_trades,
    wins,
    losses,
    winrate,
    net_pnl,
    expectancy,
    profit_factor,
    runtime_allowed,
    execution_enabled,
    verdict,
    raw_json
)
VALUES (
    %(symbol)s,
    %(source_strategy)s,
    %(strategy)s,
    %(exit_bars)s,
    %(signals)s,
    %(closed_trades)s,
    %(wins)s,
    %(losses)s,
    %(winrate)s,
    %(net_pnl)s,
    %(expectancy)s,
    %(profit_factor)s,
    false,
    false,
    %(verdict)s,
    %(raw_json)s
);
"""

def j(v):
    if isinstance(v, Decimal):
        return float(v)
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v

def main() -> int:
    print("=== LKOH SELL ONLY SCORECARD V1 ===")
    print("mode=sell_only_scorecard")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"source_strategy={SOURCE_STRATEGY}")
    print(f"strategy={STRATEGY}")
    print(f"exit_bars={EXIT_BARS}")
    print()

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL, (SYMBOL, SOURCE_STRATEGY, EXIT_BARS))
            rows = cur.fetchall()

            signals = len(rows)
            closed = [r for r in rows if r["pnl"] is not None]
            wins = [r for r in closed if float(r["pnl"]) > 0]
            losses = [r for r in closed if float(r["pnl"]) < 0]

            closed_trades = len(closed)
            wins_n = len(wins)
            losses_n = len(losses)

            net_pnl = round(sum(float(r["pnl"]) for r in closed), 6)
            expectancy = round(net_pnl / closed_trades, 6) if closed_trades else None
            winrate = round(wins_n / closed_trades * 100, 2) if closed_trades else None

            gross_profit = sum(float(r["pnl"]) for r in wins)
            gross_loss = abs(sum(float(r["pnl"]) for r in losses))
            profit_factor = round(gross_profit / gross_loss, 4) if gross_loss else None

            if closed_trades >= 300 and expectancy is not None and expectancy > 0 and (profit_factor or 0) >= 1.15:
                verdict = "LKOH_SELL_ONLY_READY_FOR_REVIEW"
            elif closed_trades >= 300 and expectancy is not None and expectancy > 0:
                verdict = "LKOH_SELL_ONLY_RESEARCH"
            else:
                verdict = "LKOH_SELL_ONLY_REJECT"

            payload = {
                "symbol": SYMBOL,
                "source_strategy": SOURCE_STRATEGY,
                "strategy": STRATEGY,
                "exit_bars": EXIT_BARS,
                "signals": signals,
                "closed_trades": closed_trades,
                "wins": wins_n,
                "losses": losses_n,
                "winrate": winrate,
                "net_pnl": net_pnl,
                "expectancy": expectancy,
                "profit_factor": profit_factor,
                "runtime_allowed": False,
                "execution_enabled": False,
                "verdict": verdict,
            }

            cur.execute(
                INSERT,
                {
                    **payload,
                    "raw_json": json.dumps(payload, ensure_ascii=False),
                },
            )

        conn.commit()

    print(
        "SELL_ONLY_ROW "
        f"signals={signals} "
        f"closed_trades={closed_trades} "
        f"wins={wins_n} "
        f"losses={losses_n} "
        f"winrate={winrate} "
        f"net_pnl={net_pnl} "
        f"expectancy={expectancy} "
        f"profit_factor={profit_factor} "
        f"verdict={verdict}"
    )

    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print(f"VERDICT={verdict}")
    print("LKOH_SELL_ONLY_SCORECARD_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
