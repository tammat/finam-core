#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITY_GUARD_STRATEGY_AFTER_RESTART_AUDIT_V1 ==="

python3 - <<'PY'
import os
import subprocess
import psycopg2

raw_active_since = subprocess.check_output(
    ["systemctl", "show", "finam-paper-pipeline.service", "-p", "ActiveEnterTimestamp", "--value"],
    text=True,
).strip()

parts = raw_active_since.split()
if len(parts) >= 4 and parts[0].isalpha():
    active_since = " ".join(parts[1:3]) + "+03:00"
else:
    active_since = raw_active_since.replace(" MSK", "+03:00")

dsn = os.getenv("DATABASE_URL")
if not dsn:
    raise SystemExit("DATABASE_URL_NOT_SET")

print("=== EQUITY_GUARD_STRATEGY_AFTER_RESTART_AUDIT_V1 ===")
print("mode=read_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print(f"raw_active_since={raw_active_since}")
print(f"active_since={active_since}")

with psycopg2.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            with runtime as (
                select symbol, strategy as runtime_strategy
                from runtime_active_universe
                where symbol like '%%@MISX'
            ),
            guard_rows as (
                select symbol, strategy as guard_strategy, timeframe, block_reason, created_at
                from runtime_guard_pre_signal_block_audit_v1
                where symbol like '%%@MISX'
                  and created_at >= %s::timestamptz
            )
            select
                g.symbol,
                r.runtime_strategy,
                g.guard_strategy,
                g.timeframe,
                g.block_reason,
                count(*)::int,
                max(g.created_at)
            from guard_rows g
            left join runtime r on r.symbol = g.symbol
            group by g.symbol, r.runtime_strategy, g.guard_strategy, g.timeframe, g.block_reason
            order by count(*) desc, g.symbol
        """, (active_since,))

        rows = cur.fetchall()
        total = legacy = volatility = mismatch = 0

        for symbol, runtime_strategy, guard_strategy, timeframe, reason, n, last_seen in rows:
            total += n
            legacy += n if guard_strategy in ("MEAN_REVERSION_EQUITY", "TREND_PULLBACK_EQUITY") else 0
            volatility += n if guard_strategy == "VOLATILITY_BREAKOUT_EQUITY" else 0
            mismatch += n if runtime_strategy and runtime_strategy != guard_strategy else 0

            print(
                "AFTER_RESTART_GUARD_ROW "
                f"symbol={symbol} runtime_strategy={runtime_strategy} "
                f"guard_strategy={guard_strategy} timeframe={timeframe} "
                f"block_reason={reason} rows={n} last_seen={last_seen}"
            )

        print(
            "AFTER_RESTART_SUMMARY "
            f"rows={total} mismatch={mismatch} "
            f"volatility_rows={volatility} legacy_rows={legacy}"
        )

        if total == 0:
            verdict = "AFTER_RESTART_WAIT_FOR_ROWS"
        elif legacy > 0:
            verdict = "AFTER_RESTART_LEGACY_STILL_WRITING"
        elif volatility > 0 and mismatch == 0:
            verdict = "AFTER_RESTART_VOLATILITY_OK"
        else:
            verdict = "AFTER_RESTART_REVIEW_REQUIRED"

        print(f"VERDICT={verdict}")
PY

echo "TEST_EQUITY_GUARD_STRATEGY_AFTER_RESTART_AUDIT_V1_OK"
