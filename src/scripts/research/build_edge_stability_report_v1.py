#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import psycopg2

WINDOWS = [
    ("7D", "7 day"),
    ("14D", "14 day"),
    ("30D", "30 day"),
    ("ALL", None),
]

print("=== EDGE_STABILITY_REPORT_V1 ===")
print("mode=read_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("telegram_send=0")

dsn = os.getenv("DATABASE_URL")

if not dsn:
    print("VERDICT=DATABASE_URL_NOT_SET")
    sys.exit(1)

with psycopg2.connect(dsn) as conn:
    with conn.cursor() as cur:

        cur.execute("""
            select distinct
                selection,
                filter_name
            from analytics_futures_rs_bottom_paper_observation_v1
            order by selection, filter_name
        """)

        candidates = cur.fetchall()

        for selection, filter_name in candidates:

            print(
                f"CANDIDATE selection={selection} "
                f"filter={filter_name}"
            )

            stable_flags = []

            for label, interval_expr in WINDOWS:

                where_window = ""

                params = [selection, filter_name]

                if interval_expr:
                    where_window = (
                        f"and source_ts >= now() - interval '{interval_expr}'"
                    )

                cur.execute(
                    f"""
                    select
                        count(*)::int as signals,
                        count(*) filter (
                            where status='SUCCESS'
                        )::int as success,
                        count(*) filter (
                            where status='FAILURE'
                        )::int as failure,
                        count(*) filter (
                            where status in ('SUCCESS','FAILURE')
                        )::int as completed,
                        avg(return_pct) filter (
                            where status in ('SUCCESS','FAILURE')
                        ) as avg_return
                    from analytics_futures_rs_bottom_paper_observation_v1
                    where selection=%s
                      and filter_name=%s
                      {where_window}
                    """,
                    params,
                )

                (
                    signals,
                    success,
                    failure,
                    completed,
                    avg_return,
                ) = cur.fetchone()

                success = success or 0
                failure = failure or 0
                completed = completed or 0

                if completed > 0:
                    winrate = success / completed
                else:
                    winrate = 0

                if failure == 0 and success > 0:
                    pf = 999
                elif failure == 0:
                    pf = 0
                else:
                    pf = success / failure

                stable_flags.append(pf)

                print(
                    f"WINDOW={label} "
                    f"signals={signals} "
                    f"completed={completed} "
                    f"success={success} "
                    f"failure={failure} "
                    f"winrate={winrate:.4f} "
                    f"avg_return_pct={avg_return} "
                    f"pf={pf:.4f}"
                )

            pf7 = stable_flags[0]
            pf14 = stable_flags[1]
            pf30 = stable_flags[2]

            if pf7 >= 1 and pf14 >= 1 and pf30 >= 1:
                verdict = "EDGE_STABLE"
            elif pf7 < pf14 < pf30:
                verdict = "EDGE_DECAYING"
            elif pf7 < 1 and pf14 < 1:
                verdict = "EDGE_BROKEN"
            else:
                verdict = "EDGE_MIXED"

            print(
                f"EDGE_VERDICT selection={selection} "
                f"filter={filter_name} "
                f"verdict={verdict}"
            )

print("VERDICT=EDGE_STABILITY_REPORT_READY")
print("TEST_EDGE_STABILITY_REPORT_V1_OK")
