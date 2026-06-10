#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SQL = """
WITH base AS (
    SELECT
        symbol,
        side,
        net_pnl,
        COALESCE(entry_ts, opened_at, closed_at) AS ts
    FROM closed_trades
    WHERE symbol='BRM6@RTSX'
      AND side='LONG'
      AND trade_source='paper'
      AND source='closed_trade_engine_v1_1'
      AND EXTRACT(HOUR FROM (COALESCE(entry_ts, opened_at) AT TIME ZONE 'Europe/Moscow'))
          BETWEEN 10 AND 13
)
SELECT
    COUNT(*) AS trades,
    COUNT(*) FILTER (WHERE net_pnl > 0) AS wins,
    COUNT(*) FILTER (WHERE net_pnl <= 0) AS losses,
    ROUND(SUM(net_pnl)::numeric,6) AS net_pnl,
    ROUND(AVG(net_pnl)::numeric,6) AS expectancy,
    ROUND(
        (
            SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END)
            /
            NULLIF(ABS(SUM(CASE WHEN net_pnl <= 0 THEN net_pnl ELSE 0 END)),0)
        )::numeric,
        4
    ) AS profit_factor,
    MIN(ts) AS first_ts,
    MAX(ts) AS last_ts
FROM base;
"""

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS runtime_governance_shadow_accumulation_v1 (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    candidate TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    session TEXT NOT NULL,
    decision TEXT NOT NULL,
    runtime_allow INTEGER NOT NULL,
    shadow_allow INTEGER NOT NULL,
    watch_allow INTEGER NOT NULL,
    trades INTEGER NOT NULL,
    wins INTEGER NOT NULL,
    losses INTEGER NOT NULL,
    net_pnl DOUBLE PRECISION NOT NULL,
    expectancy DOUBLE PRECISION NOT NULL,
    profit_factor DOUBLE PRECISION,
    first_ts TIMESTAMPTZ,
    last_ts TIMESTAMPTZ,
    reason TEXT NOT NULL
);
"""

INSERT_SQL = """
INSERT INTO runtime_governance_shadow_accumulation_v1 (
    candidate, symbol, side, session,
    decision, runtime_allow, shadow_allow, watch_allow,
    trades, wins, losses, net_pnl, expectancy, profit_factor,
    first_ts, last_ts, reason
)
VALUES (
    %(candidate)s, %(symbol)s, %(side)s, %(session)s,
    %(decision)s, %(runtime_allow)s, %(shadow_allow)s, %(watch_allow)s,
    %(trades)s, %(wins)s, %(losses)s, %(net_pnl)s, %(expectancy)s, %(profit_factor)s,
    %(first_ts)s, %(last_ts)s, %(reason)s
);
"""

def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== RUNTIME GOVERNANCE SHADOW ACCUMULATION V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("candidate=BRM6_LONG_московская_середина")
    print("decision=WATCH_ONLY")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)
            row = cur.fetchone()

            trades = int(row["trades"] or 0)
            wins = int(row["wins"] or 0)
            losses = int(row["losses"] or 0)
            net_pnl = float(row["net_pnl"] or 0)
            expectancy = float(row["expectancy"] or 0)
            pf = row["profit_factor"]
            pf_value = float(pf) if pf is not None else None

            print("ACCUMULATION_ROW "
                  f"symbol=BRM6@RTSX "
                  f"side=LONG "
                  f"session=московская_середина "
                  f"trades={trades} "
                  f"wins={wins} "
                  f"losses={losses} "
                  f"net_pnl={net_pnl} "
                  f"expectancy={expectancy} "
                  f"profit_factor={pf_value} "
                  f"first_ts={row['first_ts']} "
                  f"last_ts={row['last_ts']}")

            cur.execute(CREATE_SQL)

            item = {
                "candidate": "BRM6_LONG_московская_середина",
                "symbol": "BRM6@RTSX",
                "side": "LONG",
                "session": "московская_середина",
                "decision": "WATCH_ONLY",
                "runtime_allow": 0,
                "shadow_allow": 1,
                "watch_allow": 1,
                "trades": trades,
                "wins": wins,
                "losses": losses,
                "net_pnl": net_pnl,
                "expectancy": expectancy,
                "profit_factor": pf_value,
                "first_ts": row["first_ts"],
                "last_ts": row["last_ts"],
                "reason": "recent_decay_confirmed",
            }

            cur.execute(INSERT_SQL, item)

    print()
    print("SHADOW_DECISION_ROW runtime_allow=0 shadow_allow=1 watch_allow=1 decision=WATCH_ONLY reason=recent_decay_confirmed")
    print("VERDICT=RUNTIME_GOVERNANCE_SHADOW_ACCUMULATION_RECORDED")
    print("RUNTIME_GOVERNANCE_SHADOW_ACCUMULATION_V1_OK")

if __name__ == "__main__":
    main()
