#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row


CONFIRMATION_WINDOW_MIN = 240


def dec(v):
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def pf(pos_sum, neg_sum):
    pos_sum = dec(pos_sum)
    neg_sum = abs(dec(neg_sum))
    if neg_sum == 0:
        return None
    return pos_sum / neg_sum


def verdict(observations, pf_value):
    if observations < 10:
        return "НЕДОСТАТОЧНО_ДАННЫХ"
    if pf_value is None:
        return "НЕТ_PF"
    if pf_value >= Decimal("1.30"):
        return "ПОДТВЕРЖДЕНИЕ_УЛУЧШАЕТ_EDGE"
    if pf_value >= Decimal("1.00"):
        return "ПОДТВЕРЖДЕНИЕ_СЛАБОЕ"
    return "ПОДТВЕРЖДЕНИЕ_НЕ_УЛУЧШАЕТ_EDGE"


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    print("=== RS_BREAKOUT_CONFIRMATION_V1 ===")
    print("mode=research_read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                with rs as (
                    select
                        id,
                        symbol,
                        selection,
                        filter_name,
                        source_ts,
                        source_close,
                        future_ts,
                        future_close,
                        return_pct,
                        status
                    from analytics_futures_rs_bottom_paper_observation_v1
                    where status in ('SUCCESS','FAILURE','WAITING')
                ),
                breakout_confirm as (
                    select
                        rs.id as rs_id,
                        count(*)::int as breakout_rows,
                        min(br.created_at) as first_breakout_time
                    from rs
                    join analytics_multi_asset_breakout_row_v1 br
                      on br.symbol = rs.symbol
                     and br.created_at >= rs.source_ts
                     and br.created_at <= rs.source_ts + interval '240 minutes'
                     and (
                         br.status = 'BREAKOUT_READY'
                         or br.breakout_ok = true
                     )
                    group by rs.id
                ),
                classified as (
                    select
                        rs.*,
                        case
                            when bc.rs_id is not null then 'RS_PLUS_BREAKOUT'
                            else 'RS_ONLY'
                        end as bucket,
                        bc.breakout_rows,
                        bc.first_breakout_time
                    from rs
                    left join breakout_confirm bc on bc.rs_id = rs.id
                )
                select
                    bucket,
                    selection,
                    filter_name,
                    count(*)::int as observations,
                    count(*) filter (where status='WAITING')::int as waiting,
                    count(*) filter (where status='SUCCESS')::int as wins,
                    count(*) filter (where status='FAILURE')::int as losses,
                    count(*) filter (where status in ('SUCCESS','FAILURE'))::int as completed,
                    avg(return_pct) filter (where status in ('SUCCESS','FAILURE')) as avg_return_pct,
                    sum(return_pct) filter (where status='SUCCESS') as positive_sum,
                    sum(return_pct) filter (where status='FAILURE') as negative_sum,
                    max(first_breakout_time) as last_breakout_confirm
                from classified
                group by bucket, selection, filter_name
                order by bucket, selection, filter_name
            """)
            rows = list(cur.fetchall())

    rs_only_pf = None
    rs_plus_pf = None

    for r in rows:
        pf_value = pf(r["positive_sum"], r["negative_sum"])
        completed = int(r["completed"] or 0)
        observations = int(r["observations"] or 0)

        if r["bucket"] == "RS_ONLY":
            rs_only_pf = pf_value
        if r["bucket"] == "RS_PLUS_BREAKOUT":
            rs_plus_pf = pf_value

        print(
            "RS_BREAKOUT_CONFIRM_ROW "
            f"bucket={r['bucket']} "
            f"selection={r['selection']} "
            f"filter={r['filter_name']} "
            f"observations={observations} "
            f"waiting={r['waiting']} "
            f"completed={completed} "
            f"wins={r['wins']} "
            f"losses={r['losses']} "
            f"avg_return_pct={r['avg_return_pct']} "
            f"profit_factor={pf_value} "
            f"verdict={verdict(completed, pf_value)}"
        )

    print(f"confirmation_window_min={CONFIRMATION_WINDOW_MIN}")
    print(f"rows_total={len(rows)}")
    print(f"rs_only_pf={rs_only_pf}")
    print(f"rs_plus_breakout_pf={rs_plus_pf}")

    if rs_plus_pf is None:
        print("VERDICT=RS_BREAKOUT_CONFIRMATION_COLLECTING")
    elif rs_only_pf is not None and rs_plus_pf > rs_only_pf:
        print("VERDICT=RS_BREAKOUT_CONFIRMATION_IMPROVES_EDGE")
    else:
        print("VERDICT=RS_BREAKOUT_CONFIRMATION_NO_IMPROVEMENT_YET")

    print("TEST_RS_BREAKOUT_CONFIRMATION_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
