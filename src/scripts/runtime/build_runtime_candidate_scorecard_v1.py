#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from decimal import Decimal

import psycopg2
import psycopg2.extras

CANDIDATES = ["GDU6@RTSX", "USDRUBF@RTSX", "LKOH@MISX", "BRN6@RTSX", "NGN6@RTSX"]

DDL = """
CREATE TABLE IF NOT EXISTS runtime_candidate_scorecard (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    status text,
    source text,
    signals integer,
    trades integer,
    winrate numeric,
    expectancy numeric,
    profit_factor numeric,
    stability_ratio numeric,
    review_gate text,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    reason text,
    raw_json jsonb
);

CREATE INDEX IF NOT EXISTS idx_runtime_candidate_scorecard_symbol_created
ON runtime_candidate_scorecard(symbol, created_at DESC);
"""

SQL = """
WITH src AS (
    SELECT unnest(%s::text[]) AS symbol
),
registry AS (
    SELECT
        symbol,
        status,
        reason,
        runtime_allowed,
        execution_enabled
    FROM runtime_candidate_registry
    WHERE symbol = ANY(%s)
),
closed AS (
    SELECT
        symbol,
        COUNT(*) AS trades,
        COUNT(*) FILTER (WHERE net_pnl > 0) AS wins,
        ROUND(COALESCE(AVG(net_pnl), 0)::numeric, 6) AS expectancy,
        ROUND((
            SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END)
            / NULLIF(ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END)), 0)
        )::numeric, 4) AS profit_factor
    FROM closed_trades
    WHERE symbol = ANY(%s)
    GROUP BY symbol
),
gold_telemetry AS (
    SELECT
        symbol,
        shadow_signals,
        shadow_trades,
        shadow_winrate,
        shadow_expectancy,
        shadow_profit_factor
    FROM runtime_gold_watch_telemetry
    WHERE symbol='GDU6@RTSX'
    ORDER BY id DESC
    LIMIT 1
),
gold_stability AS (
    SELECT
        symbol,
        stability_ratio
    FROM gold_shadow_stability_monitor
    WHERE symbol='GDU6@RTSX'
    ORDER BY id DESC
    LIMIT 1
),
gold_gate AS (
    SELECT
        symbol,
        decision
    FROM gold_runtime_review_gate
    WHERE symbol='GDU6@RTSX'
    ORDER BY id DESC
    LIMIT 1
),
lkoh_sell AS (
    SELECT
        symbol,
        closed_trades,
        winrate,
        expectancy,
        profit_factor
    FROM lkoh_sell_only_scorecard
    WHERE symbol='LKOH@MISX'
    ORDER BY id DESC
    LIMIT 1
),
lkoh_gate AS (
    SELECT
        symbol,
        decision
    FROM lkoh_sell_only_review_gate
    WHERE symbol='LKOH@MISX'
    ORDER BY id DESC
    LIMIT 1
)
SELECT
    s.symbol,
    r.status,
    r.reason,
    r.runtime_allowed,
    r.execution_enabled,
    c.trades AS closed_trades,
    CASE
        WHEN c.trades > 0 THEN ROUND((c.wins::numeric / c.trades::numeric * 100), 2)
        ELSE NULL
    END AS closed_winrate,
    c.expectancy AS closed_expectancy,
    c.profit_factor AS closed_profit_factor,
    gt.shadow_signals,
    gt.shadow_trades,
    gt.shadow_winrate,
    gt.shadow_expectancy,
    gt.shadow_profit_factor,
    gs.stability_ratio,
    gg.decision AS review_gate,
    ls.closed_trades AS lkoh_sell_trades,
    ls.winrate AS lkoh_sell_winrate,
    ls.expectancy AS lkoh_sell_expectancy,
    ls.profit_factor AS lkoh_sell_profit_factor,
    lg.decision AS lkoh_review_gate
FROM src s
LEFT JOIN registry r ON r.symbol = s.symbol
LEFT JOIN closed c ON c.symbol = s.symbol
LEFT JOIN gold_telemetry gt ON gt.symbol = s.symbol
LEFT JOIN gold_stability gs ON gs.symbol = s.symbol
LEFT JOIN gold_gate gg ON gg.symbol = s.symbol
LEFT JOIN lkoh_sell ls ON ls.symbol = s.symbol
LEFT JOIN lkoh_gate lg ON lg.symbol = s.symbol
ORDER BY s.symbol;
"""

INSERT = """
INSERT INTO runtime_candidate_scorecard (
    symbol,
    status,
    source,
    signals,
    trades,
    winrate,
    expectancy,
    profit_factor,
    stability_ratio,
    review_gate,
    runtime_allowed,
    execution_enabled,
    reason,
    raw_json
)
VALUES (
    %(symbol)s,
    %(status)s,
    %(source)s,
    %(signals)s,
    %(trades)s,
    %(winrate)s,
    %(expectancy)s,
    %(profit_factor)s,
    %(stability_ratio)s,
    %(review_gate)s,
    false,
    false,
    %(reason)s,
    %(raw_json)s
);
"""

def j(v):
    if isinstance(v, Decimal):
        return float(v)
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v

def metric_view(row: dict) -> dict:
    symbol = row["symbol"]

    if symbol == "GDU6@RTSX" and row.get("shadow_trades") is not None:
        return {
            "source": "GOLD_SHADOW_FILTERED",
            "signals": row.get("shadow_signals"),
            "trades": row.get("shadow_trades"),
            "winrate": row.get("shadow_winrate"),
            "expectancy": row.get("shadow_expectancy"),
            "profit_factor": row.get("shadow_profit_factor"),
        }

    if symbol == "LKOH@MISX" and row.get("lkoh_sell_trades") is not None:
        return {
            "source": "LKOH_SELL_ONLY",
            "signals": None,
            "trades": row.get("lkoh_sell_trades"),
            "winrate": row.get("lkoh_sell_winrate"),
            "expectancy": row.get("lkoh_sell_expectancy"),
            "profit_factor": row.get("lkoh_sell_profit_factor"),
        }

    return {
        "source": "CLOSED_TRADES",
        "signals": None,
        "trades": row.get("closed_trades"),
        "winrate": row.get("closed_winrate"),
        "expectancy": row.get("closed_expectancy"),
        "profit_factor": row.get("closed_profit_factor"),
    }

def main() -> int:
    print("=== RUNTIME CANDIDATE SCORECARD V1 ===")
    print("mode=read_only_scorecard")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbols={','.join(CANDIDATES)}")
    print()

    rows_written = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL, (CANDIDATES, CANDIDATES, CANDIDATES))
            rows = cur.fetchall()

            print("SCORECARD_ROWS")

            for row in rows:
                metrics = metric_view(row)
                payload = {k: j(v) for k, v in dict(row).items()}
                payload["metrics"] = {k: j(v) for k, v in metrics.items()}

                cur.execute(
                    INSERT,
                    {
                        "symbol": row["symbol"],
                        "status": row["status"],
                        "source": metrics["source"],
                        "signals": metrics["signals"],
                        "trades": metrics["trades"],
                        "winrate": metrics["winrate"],
                        "expectancy": metrics["expectancy"],
                        "profit_factor": metrics["profit_factor"],
                        "stability_ratio": row["stability_ratio"],
                        "review_gate": row["lkoh_review_gate"] if row["symbol"] == "LKOH@MISX" else row["review_gate"],
                        "reason": row["reason"],
                        "raw_json": json.dumps(payload, ensure_ascii=False),
                    },
                )
                rows_written += 1

                print(
                    "SCORECARD_ROW "
                    f"symbol={row['symbol']} "
                    f"status={row['status']} "
                    f"source={metrics['source']} "
                    f"signals={metrics['signals']} "
                    f"trades={metrics['trades']} "
                    f"winrate={metrics['winrate']} "
                    f"expectancy={metrics['expectancy']} "
                    f"profit_factor={metrics['profit_factor']} "
                    f"stability_ratio={row['stability_ratio']} "
                    f"review_gate={row['lkoh_review_gate'] if row['symbol'] == 'LKOH@MISX' else row['review_gate']} "
                    f"runtime_allowed=0 "
                    f"execution_enabled=0"
                )

        conn.commit()

    print()
    print(f"SCORECARD_ROWS_WRITTEN={rows_written}")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=RUNTIME_CANDIDATE_SCORECARD_RECORDED")
    print("RUNTIME_CANDIDATE_SCORECARD_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
