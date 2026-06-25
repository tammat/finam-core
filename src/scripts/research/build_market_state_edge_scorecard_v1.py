#!/usr/bin/env python3

import os
import psycopg2


def main() -> int:
    print("=== MARKET_STATE_EDGE_SCORECARD_V1 ===")
    print("mode=scorecard_read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("orders_sent=0")

    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2
    if database_url.startswith("sqlite"):
        print("ERROR=SQLITE_FORBIDDEN")
        return 2

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    compact_signature,
                    canonical_signature,
                    COUNT(*) AS observations,
                    COUNT(DISTINCT symbol) AS symbols,
                    MIN(snapshot_ts) AS first_ts,
                    MAX(snapshot_ts) AS last_ts,
                    AVG(confidence) AS avg_confidence,
                    MAX(conflict_score) AS max_conflict
                FROM research.market_state_snapshots_v1
                WHERE source='runtime_shadow_market_state_v1'
                GROUP BY compact_signature, canonical_signature
                ORDER BY observations DESC, compact_signature;
            """)
            rows = cur.fetchall()

    print("")
    print("SCORECARD_ROWS")

    candidates = 0

    for row in rows:
        (
            compact_signature,
            canonical_signature,
            observations,
            symbols,
            first_ts,
            last_ts,
            avg_confidence,
            max_conflict,
        ) = row

        status = "INSUFFICIENT_OBSERVATIONS"
        if observations >= 100:
            status = "READY_FOR_PNL_LINKING"

        print(
            "SCORECARD_ROW "
            f"signature={compact_signature} "
            f"observations={observations} "
            f"symbols={symbols} "
            f"avg_confidence={float(avg_confidence):.4f} "
            f"max_conflict={float(max_conflict):.4f} "
            f"first={first_ts} "
            f"last={last_ts} "
            f"status={status}"
        )
        print(f"CANONICAL {canonical_signature}")

        if status == "READY_FOR_PNL_LINKING":
            candidates += 1

    print("")
    print(f"rows_total={len(rows)}")
    print(f"ready_for_pnl_linking={candidates}")
    print("edge_candidates=0")
    print("micro_live_candidates=0")

    print("")
    print("DESIGN_RULES")
    print("rule=scorecard_is_read_only")
    print("rule=no_pnl_until_trade_state_linking")
    print("rule=no_runtime_execution_changes")

    print("")
    print("NEXT_STEPS")
    print("next=MARKET_STATE_TRADE_LINKING_PLAN_V1")

    print("")
    print("VERDICT=MARKET_STATE_EDGE_SCORECARD_READY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
