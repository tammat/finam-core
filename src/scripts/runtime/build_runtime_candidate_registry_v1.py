#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import psycopg2
import psycopg2.extras

SYMBOLS = ["GDU6@RTSX", "USDRUBF@RTSX", "LKOH@MISX", "BRN6@RTSX", "NGN6@RTSX"]

DDL = """
CREATE TABLE IF NOT EXISTS runtime_candidate_registry (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    status text NOT NULL,
    reason text,
    source text,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    raw_json jsonb,
    CONSTRAINT uq_runtime_candidate_registry_symbol UNIQUE(symbol)
);

CREATE INDEX IF NOT EXISTS idx_runtime_candidate_registry_status
ON runtime_candidate_registry(status);
"""

SQL = """
WITH closed AS (
    SELECT
        symbol,
        COUNT(*) AS trades,
        ROUND(COALESCE(AVG(net_pnl),0)::numeric, 6) AS expectancy
    FROM closed_trades
    WHERE symbol = ANY(%s)
    GROUP BY symbol
),
gold AS (
    SELECT COUNT(*) AS shadow_signals
    FROM runtime_shadow_gold_signals
    WHERE symbol='GDU6@RTSX'
      AND strategy='gold_short_only_shadow_v1'
)
SELECT
    s.symbol,
    COALESCE(c.trades, 0) AS trades,
    COALESCE(c.expectancy, 0) AS expectancy,
    (SELECT shadow_signals FROM gold) AS gold_shadow_signals
FROM unnest(%s::text[]) AS s(symbol)
LEFT JOIN closed c ON c.symbol = s.symbol;
"""

UPSERT = """
INSERT INTO runtime_candidate_registry (
    symbol, status, reason, source, runtime_allowed, execution_enabled, raw_json, updated_at
)
VALUES (
    %(symbol)s, %(status)s, %(reason)s, %(source)s, false, false, %(raw_json)s, now()
)
ON CONFLICT (symbol) DO UPDATE
SET
    status = EXCLUDED.status,
    reason = EXCLUDED.reason,
    source = EXCLUDED.source,
    runtime_allowed = false,
    execution_enabled = false,
    raw_json = EXCLUDED.raw_json,
    updated_at = now();
"""

def classify(row: dict) -> tuple[str, str]:
    symbol = row["symbol"]
    expectancy = float(row["expectancy"] or 0)
    gold_shadow_signals = int(row["gold_shadow_signals"] or 0)

    if symbol == "GDU6@RTSX" and gold_shadow_signals >= 50:
        return "WATCH_RUNTIME", "gold_shadow_passed"
    if symbol in ("BRN6@RTSX", "NGN6@RTSX") and expectancy <= 0:
        return "REJECTED", "negative_expectancy"
    return "RESEARCH", "awaiting_shadow_validation"

def main() -> int:
    print("=== RUNTIME CANDIDATE REGISTRY V1 ===")
    print("mode=registry")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    rows_written = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL, (SYMBOLS, SYMBOLS))
            rows = cur.fetchall()

            for row in rows:
                status, reason = classify(row)
                payload = {
                    "symbol": row["symbol"],
                    "status": status,
                    "reason": reason,
                    "trades": int(row["trades"] or 0),
                    "expectancy": str(row["expectancy"]),
                    "gold_shadow_signals": int(row["gold_shadow_signals"] or 0),
                    "runtime_allowed": False,
                    "execution_enabled": False,
                }

                cur.execute(
                    UPSERT,
                    {
                        "symbol": row["symbol"],
                        "status": status,
                        "reason": reason,
                        "source": "runtime_candidate_registry_v1",
                        "raw_json": json.dumps(payload, ensure_ascii=False),
                    },
                )
                rows_written += 1

                print(
                    "REGISTRY_ROW "
                    f"symbol={row['symbol']} "
                    f"status={status} "
                    f"reason={reason} "
                    "runtime_allowed=0 "
                    "execution_enabled=0"
                )

        conn.commit()

    print()
    print(f"REGISTRY_ROWS={rows_written}")
    print("VERDICT=RUNTIME_CANDIDATE_REGISTRY_UPDATED")
    print("RUNTIME_CANDIDATE_REGISTRY_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
