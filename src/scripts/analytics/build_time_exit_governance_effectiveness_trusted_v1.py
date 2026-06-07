#!/usr/bin/env python3

from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


BR_TRUSTED_FROM = "2026-06-05 00:00:00+00"
NG_TRUSTED_FROM = "2026-06-03 00:00:00+00"


def main() -> None:

    print("=== TIME EXIT GOVERNANCE EFFECTIVENESS TRUSTED V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("policy=trusted_window")
    print()

    conn = psycopg2.connect(os.environ["DATABASE_URL"])

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

        cur.execute(
            """
            WITH trusted AS (
                SELECT
                    id,
                    symbol,
                    side,
                    net_pnl,
                    COALESCE(exit_ts, closed_at, created_at) AS ts,
                    COALESCE(NULLIF(payload->>'exit_reason',''),'NO_MATCH')
                        AS exit_reason
                FROM closed_trades
                WHERE
                (
                    symbol LIKE 'BR%%'
                    AND COALESCE(exit_ts, closed_at, created_at)
                        >= %s
                )
                OR
                (
                    symbol LIKE 'NG%%'
                    AND COALESCE(exit_ts, closed_at, created_at)
                        >= %s
                )
            )
            SELECT *
            FROM trusted
            """
            ,
            (BR_TRUSTED_FROM, NG_TRUSTED_FROM)
        )

        rows = cur.fetchall()

    br_actual = 0.0
    br_governed = 0.0
    br_blocked = 0

    ng_actual = 0.0
    ng_governed = 0.0
    ng_blocked = 0

    br_trades = 0
    ng_trades = 0

    for row in rows:

        symbol = row["symbol"]
        pnl = float(row["net_pnl"] or 0.0)
        reason = str(row["exit_reason"])

        if symbol.startswith("BR"):

            br_actual += pnl
            br_trades += 1

            if reason == "time_exit":
                br_governed += pnl
            else:
                br_governed += pnl

        elif symbol.startswith("NG"):

            ng_actual += pnl
            ng_trades += 1

            if reason == "time_exit" and pnl < 0:

                ng_blocked += 1

            else:

                ng_governed += pnl

    print("TRUSTED_EFFECTIVENESS")

    print(
        f"ROOT_ROW root=BR "
        f"trades={br_trades} "
        f"actual_net_pnl={br_actual:.6f} "
        f"governed_net_pnl={br_governed:.6f} "
        f"blocked_trades={br_blocked} "
        f"delta_pnl={(br_governed-br_actual):.6f}"
    )

    print(
        f"ROOT_ROW root=NG "
        f"trades={ng_trades} "
        f"actual_net_pnl={ng_actual:.6f} "
        f"governed_net_pnl={ng_governed:.6f} "
        f"blocked_trades={ng_blocked} "
        f"delta_pnl={(ng_governed-ng_actual):.6f}"
    )

    print()

    if ng_governed > ng_actual:
        verdict = "NG_RUNTIME_BLOCK_SUPPORTED"
    else:
        verdict = "KEEP_SHADOW"

    print("SUMMARY")
    print(f"VERDICT={verdict}")
    print("TIME_EXIT_GOVERNANCE_EFFECTIVENESS_TRUSTED_V1_OK")


if __name__ == "__main__":
    main()
