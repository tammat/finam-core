#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SQL = """
select
    symbol,
    strategy,
    timeframe,
    side,
    count(*) as signals,
    min(created_at) as first_signal,
    max(created_at) as last_signal
from runtime_shadow_gold_signals
group by 1,2,3,4
order by signals desc;
"""

def main() -> int:
    print("=== GOLD SHADOW TO PAPER WIRING AUDIT V1 ===")
    print("mode=wiring_audit")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

    allowed_rows = 0
    blocked_rows = 0

    for r in rows:
        allowed = (
            r["symbol"] == "GDU6@RTSX"
            and r["strategy"] == "gold_short_only_shadow_v1"
            and r["timeframe"] == "M5"
            and r["side"] == "SELL"
        )

        if allowed:
            allowed_rows += int(r["signals"])
            status = "PAPER_ACCUMULATION_CANDIDATE"
            reason = "active_gold_contract_short_only_m5"
        else:
            blocked_rows += int(r["signals"])
            status = "BLOCKED"
            reason = "not_active_gold_paper_accumulation_contract_or_direction"

        print(
            "GOLD_WIRING_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"side={r['side']} "
            f"signals={r['signals']} "
            f"first={r['first_signal']} "
            f"last={r['last_signal']} "
            f"status={status} "
            f"reason={reason} "
            "runtime_allow=0 execution_enabled=0"
        )

    print(
        "GOLD_WIRING_SUMMARY "
        f"allowed_signals={allowed_rows} "
        f"blocked_signals={blocked_rows} "
        "runtime_allow=0 execution_enabled=0"
    )

    print("GOLD_SHADOW_TO_PAPER_WIRING_AUDIT_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
