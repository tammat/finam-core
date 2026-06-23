#!/usr/bin/env python3
from __future__ import annotations

import os
from decimal import Decimal
import psycopg
from psycopg.rows import dict_row

TABLE = "analytics_futures_rs_bottom_paper_observation_v1"

SELECTION = "BOTTOM3"
FILTER_NAME = "COMPRESSION_RANGE"
EXCLUDED_HOURS_MSK = (12, 13, 14)

FAMILY_CASE = """
case
    when left(symbol, 2) = 'BR' then 'BRENT_FUTURES'
    when left(symbol, 2) = 'NG' then 'GAS_FUTURES'
    when left(symbol, 2) in ('GD', 'GL') then 'GOLD_FUTURES'
    when left(symbol, 7) = 'USDRUBF' then 'FX_FUTURES'
    else 'OTHER'
end
"""

def dec(v) -> Decimal:
    return Decimal(str(v or 0))

def main() -> int:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2

    print("=== RS_BOTTOM_FAMILY_STABILITY_V1 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print(f"selection={SELECTION}")
    print(f"filter_name={FILTER_NAME}")
    print("excluded_hours_msk=" + ",".join(map(str, EXCLUDED_HOURS_MSK)))

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                with src as (
                    select
                        {FAMILY_CASE} as family,
                        symbol,
                        source_ts,
                        return_pct,
                        status,
                        extract(hour from source_ts at time zone 'Europe/Moscow')::int as hour_msk
                    from {TABLE}
                    where selection = %s
                      and filter_name = %s
                      and status in ('SUCCESS','FAILURE')
                      and return_pct is not null
                      and extract(hour from source_ts at time zone 'Europe/Moscow')::int <> all(%s)
                )
                select
                    family,
                    count(*)::int as completed,
                    count(*) filter (where status='SUCCESS')::int as success,
                    count(*) filter (where status='FAILURE')::int as failure,
                    avg(return_pct) as expectancy,
                    case
                        when abs(sum(least(return_pct, 0))) > 0
                        then sum(greatest(return_pct, 0)) / abs(sum(least(return_pct, 0)))
                        else null
                    end as profit_factor,
                    avg(case when status='SUCCESS' then 1.0 else 0.0 end) as winrate,
                    count(distinct symbol)::int as symbols,
                    min(source_ts) as first_ts,
                    max(source_ts) as last_ts
                from src
                group by family
                order by profit_factor desc nulls last, completed desc;
            """, (SELECTION, FILTER_NAME, list(EXCLUDED_HOURS_MSK)))
            families = cur.fetchall()

            cur.execute(f"""
                with src as (
                    select
                        {FAMILY_CASE} as family,
                        symbol,
                        source_ts,
                        return_pct,
                        status,
                        extract(hour from source_ts at time zone 'Europe/Moscow')::int as hour_msk
                    from {TABLE}
                    where selection = %s
                      and filter_name = %s
                      and status in ('SUCCESS','FAILURE')
                      and return_pct is not null
                      and extract(hour from source_ts at time zone 'Europe/Moscow')::int <> all(%s)
                )
                select
                    family,
                    symbol,
                    count(*)::int as completed,
                    count(*) filter (where status='SUCCESS')::int as success,
                    count(*) filter (where status='FAILURE')::int as failure,
                    avg(return_pct) as expectancy,
                    case
                        when abs(sum(least(return_pct, 0))) > 0
                        then sum(greatest(return_pct, 0)) / abs(sum(least(return_pct, 0)))
                        else null
                    end as profit_factor,
                    avg(case when status='SUCCESS' then 1.0 else 0.0 end) as winrate
                from src
                group by family, symbol
                order by family, profit_factor desc nulls last, completed desc;
            """, (SELECTION, FILTER_NAME, list(EXCLUDED_HOURS_MSK)))
            symbols = cur.fetchall()

    print("\nFAMILY_ROWS")
    confirmed_families = 0
    weak_families = 0

    for r in families:
        pf = dec(r["profit_factor"])
        exp = dec(r["expectancy"])
        completed = int(r["completed"] or 0)

        if completed >= 20 and pf >= Decimal("1.3") and exp > 0:
            verdict = "CONFIRMED"
            confirmed_families += 1
        elif completed >= 10 and pf > Decimal("1.0") and exp > 0:
            verdict = "WATCH"
            weak_families += 1
        else:
            verdict = "REJECT"

        print(
            f"FAMILY_ROW family={r['family']} completed={completed} "
            f"success={r['success']} failure={r['failure']} "
            f"expectancy={r['expectancy']} profit_factor={r['profit_factor']} "
            f"winrate={r['winrate']} symbols={r['symbols']} "
            f"first_ts={r['first_ts']} last_ts={r['last_ts']} verdict={verdict}"
        )

    print("\nSYMBOL_ROWS")
    for r in symbols:
        print(
            f"SYMBOL_ROW family={r['family']} symbol={r['symbol']} "
            f"completed={r['completed']} success={r['success']} failure={r['failure']} "
            f"expectancy={r['expectancy']} profit_factor={r['profit_factor']} "
            f"winrate={r['winrate']}"
        )

    print("\nFAMILY_STABILITY_SUMMARY")
    print(f"families_total={len(families)}")
    print(f"confirmed_families={confirmed_families}")
    print(f"weak_families={weak_families}")

    if confirmed_families >= 3:
        verdict = "RS_BOTTOM_FAMILY_STABILITY_CONFIRMED"
    elif confirmed_families >= 2:
        verdict = "RS_BOTTOM_FAMILY_STABILITY_PROMISING"
    else:
        verdict = "RS_BOTTOM_FAMILY_STABILITY_WEAK"

    print("VERDICT=" + verdict)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
