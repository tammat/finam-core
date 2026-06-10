#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

CANDIDATE = "BRM6_LONG_московская_середина"

def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== RUNTIME GOVERNANCE SHADOW ACCUMULATION AUDIT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"candidate={CANDIDATE}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    COUNT(*) AS rows,
                    COUNT(*) FILTER (WHERE runtime_allow = 1) AS runtime_allow_rows,
                    COUNT(*) FILTER (WHERE shadow_allow = 1) AS shadow_allow_rows,
                    COUNT(*) FILTER (WHERE watch_allow = 1) AS watch_allow_rows,
                    COUNT(*) FILTER (WHERE decision = 'WATCH_ONLY') AS watch_only_rows,
                    MAX(created_at) AS last_created_at
                FROM runtime_governance_shadow_accumulation_v1
                WHERE candidate = %s;
            """, (CANDIDATE,))
            summary = cur.fetchone()

            cur.execute("""
                SELECT
                    id,
                    created_at,
                    candidate,
                    symbol,
                    side,
                    session,
                    decision,
                    runtime_allow,
                    shadow_allow,
                    watch_allow,
                    trades,
                    expectancy,
                    profit_factor,
                    reason
                FROM runtime_governance_shadow_accumulation_v1
                WHERE candidate = %s
                ORDER BY created_at DESC, id DESC
                LIMIT 1;
            """, (CANDIDATE,))
            latest = cur.fetchone()

    rows = int(summary["rows"] or 0)
    runtime_allow_rows = int(summary["runtime_allow_rows"] or 0)
    shadow_allow_rows = int(summary["shadow_allow_rows"] or 0)
    watch_allow_rows = int(summary["watch_allow_rows"] or 0)
    watch_only_rows = int(summary["watch_only_rows"] or 0)

    print(
        "AUDIT_SUMMARY "
        f"rows={rows} "
        f"runtime_allow_rows={runtime_allow_rows} "
        f"shadow_allow_rows={shadow_allow_rows} "
        f"watch_allow_rows={watch_allow_rows} "
        f"watch_only_rows={watch_only_rows} "
        f"last_created_at={summary['last_created_at']}"
    )

    if latest:
        print(
            "LATEST_ROW "
            f"id={latest['id']} "
            f"created_at={latest['created_at']} "
            f"candidate={latest['candidate']} "
            f"symbol={latest['symbol']} "
            f"side={latest['side']} "
            f"session={latest['session']} "
            f"decision={latest['decision']} "
            f"runtime_allow={latest['runtime_allow']} "
            f"shadow_allow={latest['shadow_allow']} "
            f"watch_allow={latest['watch_allow']} "
            f"trades={latest['trades']} "
            f"expectancy={latest['expectancy']} "
            f"profit_factor={latest['profit_factor']} "
            f"reason={latest['reason']}"
        )

    verdict = "FAIL"

    if (
        rows >= 1
        and runtime_allow_rows == 0
        and shadow_allow_rows >= 1
        and watch_allow_rows >= 1
        and watch_only_rows >= 1
        and latest
        and latest["decision"] == "WATCH_ONLY"
        and int(latest["runtime_allow"]) == 0
        and int(latest["shadow_allow"]) == 1
        and int(latest["watch_allow"]) == 1
    ):
        verdict = "PASS"

    print(f"AUDIT_VERDICT={verdict}")

    if verdict != "PASS":
        raise SystemExit(1)

    print("RUNTIME_GOVERNANCE_SHADOW_ACCUMULATION_AUDIT_V1_OK")

if __name__ == "__main__":
    main()
