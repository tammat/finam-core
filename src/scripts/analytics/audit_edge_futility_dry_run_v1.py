from __future__ import annotations

import os
from collections import Counter

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> int:
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT strategy_code,symbol_group,side_code,candidate_code,pairs,
                       metrics #>> '{futility_gate,verdict}' AS verdict,
                       metrics #>> '{futility_gate,reason}' AS reason,
                       metrics #>> '{futility_gate,active_days}' AS active_days,
                       metrics #>> '{futility_gate,net_upper_bound_r}' AS net_upper_bound_r,
                       metrics #>> '{futility_gate,delta_upper_bound_r}' AS delta_upper_bound_r,
                       workflow_stage
                FROM analytics.entry_exit_recommendation_v1 r
                LEFT JOIN analytics.entry_exit_promotion_workflow_v1 w
                  USING(strategy_code,symbol_group,side_code,candidate_code)
                WHERE r.metrics #>> '{negative_control,control_code}'='TIME_SHIFTED_ENTRY_V2'
                ORDER BY symbol_group,side_code,pairs DESC,candidate_code
            """)
            rows = [dict(row) for row in cursor.fetchall()]
    counts = Counter(str(row.get("verdict") or "NOT_EVALUATED") for row in rows)
    print("EDGE_FUTILITY_DRY_RUN_V1")
    print(f"candidates={len(rows)} decisions={dict(sorted(counts.items()))}")
    for row in rows:
        if row.get("verdict") == "REJECT":
            print("WOULD_REJECT", row["symbol_group"], row["side_code"],
                  row["candidate_code"], row.get("reason"),
                  f"pairs={row['pairs']}", f"days={row.get('active_days')}")
    print("database_writes=0 paper_changes=0 real_trading_enabled=0")
    print("VERDICT=EDGE_FUTILITY_DRY_RUN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
