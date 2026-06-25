#!/usr/bin/env python3

# ==========================================================
# MARKET_STATE_EDGE_ACCUMULATION_V1
#
# Накопление статистики по состояниям рынка.
#
# ВАЖНО
# -----
# • Только чтение research.*
# • Runtime не изменяется.
# • Execution не изменяется.
# • Реальная торговля не включается.
# ==========================================================

import os
import psycopg2


def main():
    print("=== MARKET_STATE_EDGE_ACCUMULATION_V1 ===")
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
                    canonical_signature,
                    COUNT(*) observations,
                    MIN(snapshot_ts),
                    MAX(snapshot_ts),
                    AVG(confidence),
                    MAX(conflict_score)
                FROM research.market_state_snapshots_v1
                WHERE source='runtime_shadow_market_state_v1'
                GROUP BY
                    compact_signature,
                    canonical_signature
                ORDER BY observations DESC,
                         compact_signature;
            """)

            rows = cur.fetchall()

    print()
    print("STATE_ACCUMULATION")

    for row in rows:

        (
            compact,
            canonical,
            observations,
            first_ts,
            last_ts,
            avg_confidence,
            max_conflict,
        ) = row

        print(
            "STATE "
            f"signature={compact} "
            f"observations={observations} "
            f"avg_confidence={float(avg_confidence):.4f} "
            f"max_conflict={float(max_conflict):.4f} "
            f"first={first_ts} "
            f"last={last_ts}"
        )

        print(f"CANONICAL {canonical}")

    print()
    print(f"states_total={len(rows)}")
    print(f"observations_total={sum(r[2] for r in rows)}")
    print("edge_candidates=0")
    print("research_candidates=0")
    print("micro_live_candidates=0")

    print()
    print("DESIGN_RULES")
    print("rule=accumulate_before_edge")
    print("rule=no_runtime_execution_changes")
    print("rule=shadow_is_observation_only")

    print()
    print("NEXT_STEPS")
    print("next=MARKET_STATE_EDGE_SCORECARD_V1")

    print()
    print("VERDICT=MARKET_STATE_EDGE_ACCUMULATION_READY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
