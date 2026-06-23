#!/usr/bin/env python3
from __future__ import annotations

import os
from decimal import Decimal
import psycopg
from psycopg.rows import dict_row

TABLE = "analytics_futures_rs_bottom_paper_observation_v1"
SELECTION = "BOTTOM3"
FILTER_NAME = "COMPRESSION_RANGE"
EXCLUDED_HOURS = (12, 13, 14)

FAMILY_CASE = """
case
  when left(symbol, 2) = 'BR' then 'BRENT_FUTURES'
  when left(symbol, 2) = 'NG' then 'GAS_FUTURES'
  when left(symbol, 2) in ('GD','GL') then 'GOLD_FUTURES'
  when left(symbol, 7) = 'USDRUBF' then 'FX_FUTURES'
  else 'OTHER'
end
"""

def dec(v):
    return Decimal(str(v or 0))

def classify(pf, completed):
    pf = dec(pf)
    if completed < 10:
        return "WATCH_LOW_SAMPLE"
    if pf >= Decimal("1.5"):
        return "PRIMARY"
    if pf >= Decimal("1.0"):
        return "SECONDARY"
    return "REJECT"

def main():
    db = os.environ.get("DATABASE_URL")
    if not db:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2

    print("=== RS_BOTTOM_CONTRACT_ROLLING_AUDIT_V1 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")

    with psycopg.connect(db, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                with src as (
                    select {FAMILY_CASE} as family, symbol, return_pct, status, source_ts
                    from {TABLE}
                    where selection=%s
                      and filter_name=%s
                      and status in ('SUCCESS','FAILURE')
                      and return_pct is not null
                      and extract(hour from source_ts at time zone 'Europe/Moscow')::int <> all(%s)
                ),
                agg as (
                    select family, symbol,
                           count(*)::int completed,
                           count(*) filter (where status='SUCCESS')::int success,
                           count(*) filter (where status='FAILURE')::int failure,
                           avg(return_pct) expectancy,
                           case when abs(sum(least(return_pct,0))) > 0
                                then sum(greatest(return_pct,0))/abs(sum(least(return_pct,0)))
                                else null end profit_factor,
                           avg(case when status='SUCCESS' then 1.0 else 0.0 end) winrate
                    from src
                    group by family, symbol
                ),
                fam as (
                    select family, max(profit_factor) best_pf from agg group by family
                )
                select agg.*, fam.best_pf,
                       case when fam.best_pf > 0 and agg.profit_factor is not null
                            then (fam.best_pf - agg.profit_factor)/fam.best_pf
                            else null end degradation_pct
                from agg join fam using(family)
                order by family, profit_factor desc nulls last, completed desc
            """, (SELECTION, FILTER_NAME, list(EXCLUDED_HOURS)))
            rows = cur.fetchall()

    print("\nCONTRACT_ROWS")
    for r in rows:
        verdict = classify(r["profit_factor"], int(r["completed"] or 0))
        print(
            f"CONTRACT_ROW family={r['family']} symbol={r['symbol']} "
            f"completed={r['completed']} success={r['success']} failure={r['failure']} "
            f"expectancy={r['expectancy']} profit_factor={r['profit_factor']} "
            f"winrate={r['winrate']} best_family_pf={r['best_pf']} "
            f"degradation_pct={r['degradation_pct']} verdict={verdict}"
        )

    print("\nROLLING_AUDIT_SUMMARY")
    print(f"rows={len(rows)}")
    print("VERDICT=RS_BOTTOM_CONTRACT_ROLLING_AUDIT_READY")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
