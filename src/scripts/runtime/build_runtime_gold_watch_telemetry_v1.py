#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from decimal import Decimal
import psycopg2
import psycopg2.extras

SYMBOL = "GDU6@RTSX"

DDL = """
CREATE TABLE IF NOT EXISTS runtime_gold_watch_telemetry (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    status text NOT NULL,
    last_bar_ts timestamptz,
    last_signal_ts timestamptz,
    bars_count bigint NOT NULL DEFAULT 0,
    shadow_signals bigint NOT NULL DEFAULT 0,
    shadow_trades bigint NOT NULL DEFAULT 0,
    shadow_winrate numeric,
    shadow_expectancy numeric,
    shadow_profit_factor numeric,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    reason text,
    raw_json jsonb
);

CREATE INDEX IF NOT EXISTS idx_runtime_gold_watch_telemetry_symbol_created
ON runtime_gold_watch_telemetry(symbol, created_at DESC);
"""

SQL = """
WITH registry AS (
    SELECT symbol, status, reason, runtime_allowed, execution_enabled
    FROM runtime_candidate_registry
    WHERE symbol=%s
),
bars AS (
    SELECT COUNT(*) AS bars_count, MAX(ts) AS last_bar_ts
    FROM market_bars
    WHERE symbol=%s
),
shadow_raw AS (
    SELECT
        symbol,
        timeframe,
        strategy,
        signal_ts,
        side,
        entry_price::numeric AS entry_price,
        LEAD(entry_price::numeric, 10) OVER (
            PARTITION BY symbol, timeframe, strategy
            ORDER BY signal_ts
        ) AS exit_price
    FROM runtime_shadow_gold_signals
    WHERE symbol=%s
      AND strategy='gold_short_only_shadow_v1'
),
shadow_scored AS (
    SELECT
        *,
        CASE
            WHEN exit_price IS NULL THEN NULL
            WHEN side='SELL' THEN entry_price - exit_price
            ELSE exit_price - entry_price
        END AS pnl
    FROM shadow_raw
),
shadow AS (
    SELECT
        COUNT(*) AS shadow_signals,
        COUNT(*) FILTER (WHERE pnl IS NOT NULL) AS shadow_trades,
        COUNT(*) FILTER (WHERE pnl > 0) AS shadow_wins,
        MAX(signal_ts) AS last_signal_ts,
        ROUND(CASE
            WHEN COUNT(*) FILTER (WHERE pnl IS NOT NULL) > 0
            THEN COUNT(*) FILTER (WHERE pnl > 0)::numeric
                 / COUNT(*) FILTER (WHERE pnl IS NOT NULL)::numeric * 100
            ELSE NULL
        END, 2) AS shadow_winrate,
        ROUND(COALESCE(AVG(pnl),0)::numeric, 6) AS shadow_expectancy,
        ROUND((
            SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END)
            / NULLIF(ABS(SUM(CASE WHEN pnl < 0 THEN pnl ELSE 0 END)), 0)
        )::numeric, 4) AS shadow_profit_factor
    FROM shadow_scored
)
SELECT
    r.symbol,
    r.status,
    r.reason,
    r.runtime_allowed,
    r.execution_enabled,
    b.bars_count,
    b.last_bar_ts,
    s.shadow_signals,
    s.shadow_trades,
    s.shadow_winrate,
    s.shadow_expectancy,
    s.shadow_profit_factor,
    s.last_signal_ts
FROM registry r
LEFT JOIN bars b ON true
LEFT JOIN shadow s ON true;
"""

INSERT = """
INSERT INTO runtime_gold_watch_telemetry (
    symbol,
    status,
    last_bar_ts,
    last_signal_ts,
    bars_count,
    shadow_signals,
    shadow_trades,
    shadow_winrate,
    shadow_expectancy,
    shadow_profit_factor,
    runtime_allowed,
    execution_enabled,
    reason,
    raw_json
)
VALUES (
    %(symbol)s,
    %(status)s,
    %(last_bar_ts)s,
    %(last_signal_ts)s,
    %(bars_count)s,
    %(shadow_signals)s,
    %(shadow_trades)s,
    %(shadow_winrate)s,
    %(shadow_expectancy)s,
    %(shadow_profit_factor)s,
    %(runtime_allowed)s,
    %(execution_enabled)s,
    %(reason)s,
    %(raw_json)s
);
"""

def main() -> int:
    print("=== RUNTIME GOLD WATCH TELEMETRY V1 ===")
    print("mode=watch_telemetry")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print()

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL, (SYMBOL, SYMBOL, SYMBOL))
            row = cur.fetchone()

            if not row:
                print("TELEMETRY_ERROR reason=registry_row_missing")
                return 1

            # GOLD_WATCH_TELEMETRY_READY_FOR_RUNTIME_REVIEW_STATUS_V1
            # Русский комментарий:
            # READY_FOR_RUNTIME_REVIEW — допустимый review-статус для telemetry.
            # Он не должен ронять oneshot systemd service.
            allowed_statuses = {
                "WATCH_RUNTIME_ACTIVE",
                "READY_FOR_RUNTIME_REVIEW",
            }

            if row["status"] not in allowed_statuses:
                print(
                    "TELEMETRY_ERROR "
                    f"reason=invalid_status status={row['status']}"
                )
                return 1

            if row["runtime_allowed"] is not False or row["execution_enabled"] is not False:
                print("TELEMETRY_ERROR reason=safety_flags_enabled")
                return 1

            payload = dict(row)
            for k, v in list(payload.items()):
                if isinstance(v, Decimal):
                    payload[k] = float(v)
                elif hasattr(v, "isoformat"):
                    payload[k] = v.isoformat()

            cur.execute(
                INSERT,
                {
                    "symbol": row["symbol"],
                    "status": row["status"],
                    "last_bar_ts": row["last_bar_ts"],
                    "last_signal_ts": row["last_signal_ts"],
                    "bars_count": row["bars_count"] or 0,
                    "shadow_signals": row["shadow_signals"] or 0,
                    "shadow_trades": row["shadow_trades"] or 0,
                    "shadow_winrate": row["shadow_winrate"],
                    "shadow_expectancy": row["shadow_expectancy"],
                    "shadow_profit_factor": row["shadow_profit_factor"],
                    "runtime_allowed": False,
                    "execution_enabled": False,
                    "reason": row["reason"],
                    "raw_json": json.dumps(payload, ensure_ascii=False),
                },
            )

        conn.commit()

    print(
        "TELEMETRY_ROW "
        f"symbol={row['symbol']} "
        f"status={row['status']} "
        f"bars_count={row['bars_count']} "
        f"last_bar_ts={row['last_bar_ts']} "
        f"shadow_signals={row['shadow_signals']} "
        f"shadow_trades={row['shadow_trades']} "
        f"shadow_winrate={row['shadow_winrate']} "
        f"shadow_expectancy={row['shadow_expectancy']} "
        f"shadow_profit_factor={row['shadow_profit_factor']} "
        f"last_signal_ts={row['last_signal_ts']} "
        "runtime_allowed=0 "
        "execution_enabled=0"
    )

    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=GOLD_WATCH_TELEMETRY_RECORDED")
    print("RUNTIME_GOLD_WATCH_TELEMETRY_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
