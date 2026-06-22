#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

import psycopg2


def print_header() -> None:
    print("=== EDGE_STABILITY_DATA_AUDIT_V1 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")


def table_exists(cur, table_name: str) -> bool:
    cur.execute("select to_regclass(%s)", (table_name,))
    return bool(cur.fetchone()[0])


def table_columns(cur, table_name: str) -> set[str]:
    cur.execute(
        """
        select column_name
        from information_schema.columns
        where table_schema='public'
          and table_name=%s
        """,
        (table_name,),
    )
    return {r[0] for r in cur.fetchall()}


def main() -> int:
    print_header()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("VERDICT=EDGE_STABILITY_DATA_AUDIT_DATABASE_URL_NOT_SET")
        return 1

    paper_table = "analytics_futures_rs_bottom_paper_observation_v1"
    scorecard_table = "analytics_futures_rs_bottom_forward_scorecard_v1"

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            paper_exists = table_exists(cur, paper_table)
            scorecard_exists = table_exists(cur, scorecard_table)

            print(f"PAPER_TABLE_EXISTS={int(paper_exists)}")
            print(f"SCORECARD_TABLE_EXISTS={int(scorecard_exists)}")

            if not paper_exists:
                print("VERDICT=EDGE_STABILITY_DATA_AUDIT_NO_PAPER_TABLE")
                return 1

            cols = table_columns(cur, paper_table)

            has_source_ts = "source_ts" in cols
            has_status = "status" in cols
            has_return_pct = "return_pct" in cols
            has_selection = "selection" in cols
            has_filter_name = "filter_name" in cols

            print(f"HAS_SOURCE_TS={int(has_source_ts)}")
            print(f"HAS_STATUS={int(has_status)}")
            print(f"HAS_RETURN_PCT={int(has_return_pct)}")
            print(f"HAS_SELECTION={int(has_selection)}")
            print(f"HAS_FILTER_NAME={int(has_filter_name)}")

            required_ok = all(
                [
                    has_source_ts,
                    has_status,
                    has_return_pct,
                    has_selection,
                    has_filter_name,
                ]
            )

            if not required_ok:
                print("VERDICT=EDGE_STABILITY_DATA_AUDIT_REQUIRED_COLUMNS_MISSING")
                return 1

            cur.execute(
                f"""
                select
                    count(*)::int,
                    min(source_ts),
                    max(source_ts)
                from {paper_table}
                """
            )
            total_rows, first_ts, last_ts = cur.fetchone()

            print(f"ROWS_TOTAL={total_rows}")
            print(f"FIRST_TS={first_ts}")
            print(f"LAST_TS={last_ts}")

            for days in (7, 14, 30):
                cur.execute(
                    f"""
                    select count(*)::int
                    from {paper_table}
                    where source_ts >= now() - (%s::text || ' days')::interval
                    """,
                    (days,),
                )
                print(f"WINDOW_{days}D={cur.fetchone()[0]}")

            cur.execute(
                f"""
                select
                    selection,
                    filter_name,
                    count(*)::int as rows_total,
                    count(*) filter (where status='WAITING')::int as waiting,
                    count(*) filter (where status='SUCCESS')::int as success,
                    count(*) filter (where status='FAILURE')::int as failure,
                    count(*) filter (where status in ('SUCCESS','FAILURE'))::int as completed,
                    round(avg(return_pct) filter (where status in ('SUCCESS','FAILURE')), 6) as avg_return_pct
                from {paper_table}
                group by selection, filter_name
                order by completed desc, selection, filter_name
                """
            )

            for row in cur.fetchall():
                (
                    selection,
                    filter_name,
                    rows_total,
                    waiting,
                    success,
                    failure,
                    completed,
                    avg_return_pct,
                ) = row
                print(
                    "AUDIT_GROUP_ROW "
                    f"selection={selection} "
                    f"filter={filter_name} "
                    f"rows={rows_total} "
                    f"waiting={waiting} "
                    f"success={success} "
                    f"failure={failure} "
                    f"completed={completed} "
                    f"avg_return_pct={avg_return_pct}"
                )

    print("VERDICT=EDGE_STABILITY_DATA_AUDIT_READY")
    print("TEST_EDGE_STABILITY_DATA_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
