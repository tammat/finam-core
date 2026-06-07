#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SOURCE = "closed_trade_engine_v1_1"


def db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL_NOT_SET")
    return url


def main() -> None:
    print("=== TIME EXIT GOVERNANCE RUNTIME DECISION V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"source={SOURCE}")
    print()

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    CASE
                        WHEN left(symbol, 2) = 'BR' THEN 'BR'
                        WHEN left(symbol, 2) = 'NG' THEN 'NG'
                        ELSE 'OTHER'
                    END AS root,
                    count(*) AS trades,
                    count(*) FILTER (
                        WHERE payload->>'exit_reason' ILIKE 'time_exit'
                           OR payload->>'exit_reason' ILIKE 'TIME_EXIT'
                           OR payload->>'exit_reason' ILIKE 'historical_time_exit'
                    ) AS time_exit_trades,
                    sum(net_pnl) AS net_pnl,
                    sum(net_pnl) FILTER (
                        WHERE payload->>'exit_reason' ILIKE 'time_exit'
                           OR payload->>'exit_reason' ILIKE 'TIME_EXIT'
                           OR payload->>'exit_reason' ILIKE 'historical_time_exit'
                    ) AS time_exit_net_pnl,
                    sum(net_pnl) FILTER (
                        WHERE (
                            payload->>'exit_reason' ILIKE 'time_exit'
                            OR payload->>'exit_reason' ILIKE 'TIME_EXIT'
                            OR payload->>'exit_reason' ILIKE 'historical_time_exit'
                        )
                        AND net_pnl < 0
                    ) AS negative_time_exit_net_pnl,
                    count(*) FILTER (
                        WHERE (
                            payload->>'exit_reason' ILIKE 'time_exit'
                            OR payload->>'exit_reason' ILIKE 'TIME_EXIT'
                            OR payload->>'exit_reason' ILIKE 'historical_time_exit'
                        )
                        AND net_pnl < 0
                    ) AS negative_time_exit_trades
                FROM closed_trades
                WHERE source = %s
                  AND left(symbol, 2) IN ('BR','NG')
                GROUP BY 1
                ORDER BY 1
            """, (SOURCE,))

            rows = cur.fetchall()

    print("INPUT_METRICS")
    for r in rows:
        root = r["root"]
        trades = int(r["trades"] or 0)
        time_exit_trades = int(r["time_exit_trades"] or 0)
        net_pnl = float(r["net_pnl"] or 0.0)
        time_exit_net_pnl = float(r["time_exit_net_pnl"] or 0.0)
        negative_time_exit_net_pnl = float(r["negative_time_exit_net_pnl"] or 0.0)
        negative_time_exit_trades = int(r["negative_time_exit_trades"] or 0)

        print(
            f"METRIC_ROW root={root} trades={trades} "
            f"time_exit_trades={time_exit_trades} net_pnl={net_pnl:.6f} "
            f"time_exit_net_pnl={time_exit_net_pnl:.6f} "
            f"negative_time_exit_trades={negative_time_exit_trades} "
            f"negative_time_exit_net_pnl={negative_time_exit_net_pnl:.6f}"
        )

    print()
    print("RUNTIME_DECISION")

    for r in rows:
        root = r["root"]
        negative_time_exit_trades = int(r["negative_time_exit_trades"] or 0)
        negative_time_exit_net_pnl = float(r["negative_time_exit_net_pnl"] or 0.0)
        time_exit_net_pnl = float(r["time_exit_net_pnl"] or 0.0)

        if root == "BR":
            runtime_state = "KEEP_SHADOW"
            action = "DO_NOT_ENABLE_RUNTIME_BLOCK"
            reason = "br_time_exit_blocking_would_reduce_pnl_after_duplicate_cleanup"
            env = "ENABLE_BR_TIME_EXIT_GOVERNANCE_V1=0"

        elif root == "NG" and negative_time_exit_trades >= 20 and negative_time_exit_net_pnl < 0:
            runtime_state = "ENABLE_CANDIDATE_PAPER_ONLY"
            action = "ENABLE_NG_NEGATIVE_TIME_EXIT_BLOCK_IN_PAPER_ONLY"
            reason = "ng_negative_time_exit_has_negative_pnl_after_duplicate_cleanup"
            env = "ENABLE_NG_TIME_EXIT_GOVERNANCE_V1=1"

        else:
            runtime_state = "KEEP_SHADOW"
            action = "DO_NOT_ENABLE_RUNTIME_BLOCK"
            reason = "insufficient_or_non_negative_negative_time_exit_sample"
            env = f"ENABLE_{root}_TIME_EXIT_GOVERNANCE_V1=0"

        print(
            f"DECISION_ROW root={root} runtime_state={runtime_state} "
            f"action={action} reason={reason} "
            f"time_exit_net_pnl={time_exit_net_pnl:.6f} "
            f"negative_time_exit_trades={negative_time_exit_trades} "
            f"negative_time_exit_net_pnl={negative_time_exit_net_pnl:.6f} "
            f"env={env}"
        )

    print()
    print("POLICY_MATRIX")
    print("POLICY_ROW root=BR reason=time_exit mode=shadow_only runtime_block=0")
    print("POLICY_ROW root=NG reason=time_exit pnl_negative=true mode=paper_only_candidate runtime_block=1")
    print("POLICY_ROW root=NG reason=time_exit pnl_negative=false mode=allow runtime_block=0")
    print("POLICY_ROW root=BR_NG reason=not_time_exit mode=pass runtime_block=0")
    print()
    print("VERDICT=TIME_EXIT_GOVERNANCE_RUNTIME_DECISION_RECORDED")
    print("TIME_EXIT_GOVERNANCE_RUNTIME_DECISION_V1_OK")


if __name__ == "__main__":
    main()
