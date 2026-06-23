#!/usr/bin/env python3
import os
import psycopg2
from decimal import Decimal

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("DATABASE_URL is not set")

GOOD_SYMBOLS = ("GLU6@RTSX", "GDU6@RTSX", "BRN6@RTSX", "NGM6@RTSX", "USDRUBF@RTSX")
BAD_HOURS = (12, 13, 14)

def main() -> int:
    print("=== RS_BOTTOM_SESSION_FILTER_RESEARCH_V1 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                with src as (
                    select
                        symbol,
                        selection,
                        filter_name,
                        extract(hour from source_ts at time zone 'Europe/Moscow')::int as hour_msk,
                        status,
                        return_pct::numeric as return_pct
                    from analytics_futures_rs_bottom_paper_observation_v1
                    where status in ('SUCCESS','FAILURE')
                ),
                filtered as (
                    select *
                    from src
                    where symbol = any(%s)
                      and hour_msk <> all(%s)
                ),
                agg as (
                    select
                        selection,
                        filter_name,
                        count(*) as completed,
                        count(*) filter (where status='SUCCESS') as success,
                        count(*) filter (where status='FAILURE') as failure,
                        sum(greatest(return_pct,0)) as positive_sum,
                        sum(abs(least(return_pct,0))) as negative_sum,
                        avg(return_pct) as expectancy
                    from filtered
                    group by selection, filter_name
                )
                select
                    selection,
                    filter_name,
                    completed,
                    success,
                    failure,
                    positive_sum,
                    negative_sum,
                    expectancy,
                    case
                        when negative_sum > 0 then positive_sum / negative_sum
                        when positive_sum > 0 then null
                        else 0
                    end as pf
                from agg
                order by pf desc nulls last, completed desc;
            """, (list(GOOD_SYMBOLS), list(BAD_HOURS)))

            rows = cur.fetchall()

            positive_candidates = 0
            for r in rows:
                selection, filt, completed, success, failure, pos, neg, exp, pf = r
                candidate = (
                    completed >= 100
                    and exp is not None and Decimal(exp) > 0
                    and pf is not None and Decimal(pf) >= Decimal("1.2")
                )
                if candidate:
                    positive_candidates += 1
                print(
                    "SESSION_FILTER_ROW "
                    f"selection={selection} filter={filt} completed={completed} "
                    f"success={success} failure={failure} "
                    f"expectancy={exp} pf={pf} "
                    f"verdict={'CANDIDATE' if candidate else 'REJECT'}"
                )

            cur.execute("""
                with src as (
                    select
                        symbol,
                        extract(hour from source_ts at time zone 'Europe/Moscow')::int as hour_msk,
                        status,
                        return_pct::numeric as return_pct
                    from analytics_futures_rs_bottom_paper_observation_v1
                    where status in ('SUCCESS','FAILURE')
                      and symbol = any(%s)
                      and extract(hour from source_ts at time zone 'Europe/Moscow')::int <> all(%s)
                )
                select
                    symbol,
                    count(*) as completed,
                    count(*) filter (where status='SUCCESS') as success,
                    count(*) filter (where status='FAILURE') as failure,
                    avg(return_pct) as expectancy,
                    case
                        when sum(abs(least(return_pct,0))) > 0
                        then sum(greatest(return_pct,0)) / sum(abs(least(return_pct,0)))
                        when sum(greatest(return_pct,0)) > 0 then null
                        else 0
                    end as pf
                from src
                group by symbol
                order by pf desc nulls last, completed desc;
            """, (list(GOOD_SYMBOLS), list(BAD_HOURS)))

            for r in cur.fetchall():
                symbol, completed, success, failure, exp, pf = r
                print(
                    "SESSION_FILTER_SYMBOL_ROW "
                    f"symbol={symbol} completed={completed} success={success} failure={failure} "
                    f"expectancy={exp} pf={pf}"
                )

            print("")
            print("RS_BOTTOM_SESSION_FILTER_RESEARCH_SUMMARY")
            print(f"allowed_symbols={','.join(GOOD_SYMBOLS)}")
            print(f"excluded_hours_msk={','.join(map(str, BAD_HOURS))}")
            print(f"rows={len(rows)}")
            print(f"positive_candidates={positive_candidates}")
            print("db_update=0")
            print("runtime_changed=0")
            print("execution_changed=0")

            if positive_candidates > 0:
                print("VERDICT=RS_BOTTOM_SESSION_FILTER_HAS_CANDIDATES")
            else:
                print("VERDICT=RS_BOTTOM_SESSION_FILTER_NO_POSITIVE_EDGE")

        return 0
    finally:
        conn.close()

if __name__ == "__main__":
    raise SystemExit(main())
