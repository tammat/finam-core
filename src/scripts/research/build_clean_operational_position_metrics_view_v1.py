#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


CREATE_SQL = """
drop view if exists clean_operational_position_metrics_v1;

create view clean_operational_position_metrics_v1 as
select
    count(*) filter (
        where operational_status = 'OPEN_PAPER_LONG_TAIL'
    )::int as current_position_count,

    count(*) filter (
        where operational_status = 'CLEAN_V3_FLAT'
    )::int as clean_flat_count,

    count(*) filter (
        where operational_status = 'CLEAN_V3_OPEN_REVIEW'
    )::int as clean_open_review_count,

    count(*) filter (
        where operational_status = 'QUARANTINE_CONTAMINATED_TAIL'
    )::int as quarantine_count,

    count(*) filter (
        where operational_status = 'EXCLUDE_HISTORICAL_TAIL'
    )::int as excluded_count,

    round(
        coalesce(sum(net_qty) filter (
            where operational_status = 'OPEN_PAPER_LONG_TAIL'
        ), 0)::numeric,
        6
    ) as current_net_qty_sum,

    count(*) filter (
        where include_in_clean_operational_view = true
    )::int as included_rows,

    count(*) filter (
        where include_in_clean_operational_view = false
    )::int as excluded_or_quarantined_rows,

    round(
        coalesce(sum(v3_pnl) filter (
            where include_in_clean_operational_view = true
        ), 0)::numeric,
        6
    ) as included_v3_pnl
from clean_operational_position_view_v1;
"""


REPORT_SQL = """
select
    current_position_count,
    clean_flat_count,
    clean_open_review_count,
    quarantine_count,
    excluded_count,
    current_net_qty_sum,
    included_rows,
    excluded_or_quarantined_rows,
    included_v3_pnl
from clean_operational_position_metrics_v1;
"""


def main() -> int:
    print("=== CLEAN OPERATIONAL POSITION METRICS VIEW V1 ===")
    print("mode=create_view")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(CREATE_SQL)
            conn.commit()

            cur.execute(REPORT_SQL)
            row = cur.fetchone()

    print(
        "METRICS_ROW "
        f"current_position_count={row['current_position_count']} "
        f"clean_flat_count={row['clean_flat_count']} "
        f"clean_open_review_count={row['clean_open_review_count']} "
        f"quarantine_count={row['quarantine_count']} "
        f"excluded_count={row['excluded_count']} "
        f"current_net_qty_sum={row['current_net_qty_sum']} "
        f"included_rows={row['included_rows']} "
        f"excluded_or_quarantined_rows={row['excluded_or_quarantined_rows']} "
        f"included_v3_pnl={row['included_v3_pnl']}"
    )

    failed = []

    # Русский комментарий:
    # Эти два статуса зафиксированы архитектурным решением:
    # USDRUBF в quarantine, BRM6 в excluded.
    if int(row["quarantine_count"] or 0) != 1:
        failed.append(f"quarantine_count={row['quarantine_count']} expected=1")

    if int(row["excluded_count"] or 0) != 1:
        failed.append(f"excluded_count={row['excluded_count']} expected=1")

    # Русский комментарий:
    # Количество flat/open clean строк может меняться по мере forward accumulation,
    # поэтому проверяем не точное число, а консистентность.
    current_position_count = int(row["current_position_count"] or 0)
    clean_flat_count = int(row["clean_flat_count"] or 0)
    clean_open_review_count = int(row["clean_open_review_count"] or 0)
    included_rows = int(row["included_rows"] or 0)

    expected_included = current_position_count + clean_flat_count + clean_open_review_count
    if included_rows != expected_included:
        failed.append(
            f"included_rows={included_rows} expected={expected_included}"
        )

    if failed:
        print("VERDICT=METRICS_VIEW_CHECK_FAILED " + " ".join(failed))
        raise SystemExit(1)

    print("VERDICT=CLEAN_OPERATIONAL_POSITION_METRICS_VIEW_READY")
    print("CLEAN_OPERATIONAL_POSITION_METRICS_VIEW_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
