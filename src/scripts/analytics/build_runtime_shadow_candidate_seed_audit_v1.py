#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SOURCE = "runtime_shadow_candidate_seed_v1"

def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== RUNTIME SHADOW CANDIDATE SEED AUDIT V1 ===")
    print("mode=seed_audit")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"source={SOURCE}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    COUNT(*) AS rows,
                    COUNT(*) FILTER (WHERE symbol='USDRUBF@RTSX') AS usd_rows,
                    COUNT(*) FILTER (WHERE symbol='LKOH@MISX') AS lkoh_rows,
                    COUNT(*) FILTER (WHERE shadow_only=1) AS shadow_only_rows,
                    COUNT(*) FILTER (WHERE runtime_allow=1) AS runtime_allow_rows,
                    COUNT(*) FILTER (WHERE execution_enabled=1) AS execution_enabled_rows
                FROM runtime_shadow_candidate_signals_v1
                WHERE source=%s;
            """, (SOURCE,))
            s = cur.fetchone()

            cur.execute("""
                SELECT
                    symbol,
                    strategy,
                    timeframe,
                    side,
                    shadow_only,
                    runtime_allow,
                    execution_enabled,
                    reason,
                    created_at
                FROM runtime_shadow_candidate_signals_v1
                WHERE source=%s
                ORDER BY symbol;
            """, (SOURCE,))
            rows = cur.fetchall()

    total = int(s["rows"] or 0)
    usd = int(s["usd_rows"] or 0)
    lkoh = int(s["lkoh_rows"] or 0)
    shadow_only = int(s["shadow_only_rows"] or 0)
    runtime_allow = int(s["runtime_allow_rows"] or 0)
    execution_enabled = int(s["execution_enabled_rows"] or 0)

    print(
        "AUDIT_SUMMARY "
        f"rows={total} "
        f"usd_rows={usd} "
        f"lkoh_rows={lkoh} "
        f"shadow_only_rows={shadow_only} "
        f"runtime_allow_rows={runtime_allow} "
        f"execution_enabled_rows={execution_enabled}"
    )

    print("AUDIT_ROWS")
    for r in rows:
        print(
            "AUDIT_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"side={r['side']} "
            f"shadow_only={r['shadow_only']} "
            f"runtime_allow={r['runtime_allow']} "
            f"execution_enabled={r['execution_enabled']} "
            f"reason={r['reason']} "
            f"created_at={r['created_at']}"
        )

    verdict = "PASS" if (
        total == 2
        and usd == 1
        and lkoh == 1
        and shadow_only == 2
        and runtime_allow == 0
        and execution_enabled == 0
    ) else "FAIL"

    print()
    print(f"AUDIT_VERDICT={verdict}")

    if verdict != "PASS":
        raise SystemExit(1)

    print("RUNTIME_SHADOW_CANDIDATE_SEED_AUDIT_V1_OK")

if __name__ == "__main__":
    main()
