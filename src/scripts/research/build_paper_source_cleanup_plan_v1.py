#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DDL = """
create table if not exists paper_source_cleanup_plan_v1 (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    source_status text not null,
    origin text,
    trade_source text,

    rows_count bigint not null,

    cleanup_action text not null,
    research_allowed boolean not null,
    runtime_allowed boolean not null,

    execution_enabled boolean not null default false
);
"""

TRUNCATE = """
truncate table paper_source_cleanup_plan_v1;
"""

SQL = """
select
    coalesce(origin,'NULL') as origin,
    coalesce(trade_source,'NULL') as trade_source,
    count(*) as rows_count
from trades
group by 1,2
order by rows_count desc;
"""

INSERT = """
insert into paper_source_cleanup_plan_v1 (
    source_status,
    origin,
    trade_source,
    rows_count,
    cleanup_action,
    research_allowed,
    runtime_allowed,
    execution_enabled
)
values (
    %(source_status)s,
    %(origin)s,
    %(trade_source)s,
    %(rows_count)s,
    %(cleanup_action)s,
    %(research_allowed)s,
    %(runtime_allowed)s,
    false
);
"""

def classify(origin: str, trade_source: str):
    if origin == "paper":
        return (
            "CLEAN_PAPER",
            "KEEP_AND_ACCUMULATE",
            True,
            False,
        )

    if origin == "NULL":
        return (
            "DIRTY_NULL_ORIGIN",
            "QUARANTINE_FROM_RESEARCH",
            False,
            False,
        )

    if origin == "backfill_from_fills":
        return (
            "DIRTY_BACKFILL",
            "KEEP_HISTORY_EXCLUDE_RESEARCH",
            False,
            False,
        )

    if origin in (
        "historical_signal_replay",
        "replay_br_pipeline",
    ):
        return (
            "DIRTY_REPLAY",
            "KEEP_HISTORY_EXCLUDE_RESEARCH",
            False,
            False,
        )

    if trade_source == "real_dry_run":
        return (
            "REAL_DRY_RUN",
            "SEPARATE_REALISM_BUCKET",
            False,
            False,
        )

    if trade_source == "paper_test":
        return (
            "PAPER_TEST",
            "IGNORE_TEST_DATA",
            False,
            False,
        )

    return (
        "UNKNOWN",
        "MANUAL_REVIEW",
        False,
        False,
    )

def main() -> int:
    print("=== PAPER SOURCE CLEANUP PLAN V1 ===")
    print("mode=planning_only")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            cur.execute(DDL)
            cur.execute(TRUNCATE)

            cur.execute(SQL)
            rows = cur.fetchall()

            for r in rows:
                status, action, research, runtime = classify(
                    r["origin"],
                    r["trade_source"]
                )

                cur.execute(
                    INSERT,
                    {
                        "source_status": status,
                        "origin": r["origin"],
                        "trade_source": r["trade_source"],
                        "rows_count": r["rows_count"],
                        "cleanup_action": action,
                        "research_allowed": research,
                        "runtime_allowed": runtime,
                    }
                )

        conn.commit()

    print("PAPER_SOURCE_CLEANUP_PLAN_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
