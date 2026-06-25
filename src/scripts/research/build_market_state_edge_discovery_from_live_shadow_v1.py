#!/usr/bin/env python3

# ==========================================================
# MARKET_STATE_EDGE_DISCOVERY_FROM_LIVE_SHADOW_V1
#
# Анализ состояний рынка, накопленных Shadow Feed.
#
# ВАЖНО
# -----
# • Только чтение.
# • Runtime не изменяется.
# • Execution не изменяется.
# • Реальная торговля не включается.
# ==========================================================

import os
import psycopg2


def main():
    print("=== MARKET_STATE_EDGE_DISCOVERY_FROM_LIVE_SHADOW_V1 ===")
    print("mode=research_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("orders_sent=0")

    db = os.environ.get("DATABASE_URL", "")

    if not db:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2

    if db.startswith("sqlite"):
        print("ERROR=SQLITE_FORBIDDEN")
        return 2

    with psycopg2.connect(db) as conn:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT
                    compact_signature,
                    COUNT(*),
                    MIN(snapshot_ts),
                    MAX(snapshot_ts)
                FROM research.market_state_snapshots_v1
                WHERE source='runtime_shadow_market_state_v1'
                GROUP BY compact_signature
                ORDER BY COUNT(*) DESC;
            """)

            rows = cur.fetchall()

    print()
    print("STATE_DISCOVERY")

    for signature, cnt, first_ts, last_ts in rows:
        print(
            f"STATE signature={signature} "
            f"observations={cnt} "
            f"first={first_ts} "
            f"last={last_ts}"
        )

    print()
    print(f"states_total={len(rows)}")
    print("edge_candidates=0")
    print("research_candidates=0")
    print("micro_live_candidates=0")
    print("shadow_only=1")

    print()
    print("DESIGN_RULES")
    print("rule=shadow_is_observation_only")
    print("rule=no_pnl_analysis_yet")
    print("rule=no_runtime_execution_changes")

    print()
    print("NEXT_STEPS")
    print("next=MARKET_STATE_EDGE_ACCUMULATION_V1")

    print()
    print("VERDICT=MARKET_STATE_EDGE_DISCOVERY_SHADOW_BASELINE_READY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
