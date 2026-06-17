#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


DDL = """
create or replace function ngq6_paper_trade_identity_guard_v1()
returns trigger as $$
begin
    -- Русский комментарий:
    -- Узкий guard только для NGQ6 paper accumulation.
    -- Если trades приходит без strategy/timeframe или с LIVE,
    -- нормализуем в clean V3 identity: NG_CONSERVATIVE_BREAKOUT_M1 / M1.
    if new.symbol = 'NGQ6@RTSX'
       and coalesce(new.trade_source, '') = 'paper'
       and coalesce(new.origin, 'paper') = 'paper'
    then
        if coalesce(new.strategy, '') in ('', 'UNKNOWN', 'UNKNOWN_STRATEGY') then
            new.strategy := 'NG_CONSERVATIVE_BREAKOUT_M1';
        end if;

        if coalesce(new.timeframe, '') in ('', 'LIVE', 'UNKNOWN', 'UNKNOWN_TIMEFRAME') then
            new.timeframe := 'M1';
        end if;
    end if;

    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_ngq6_paper_trade_identity_guard_v1 on trades;

create trigger trg_ngq6_paper_trade_identity_guard_v1
before insert or update of symbol, strategy, timeframe, origin, trade_source
on trades
for each row
execute function ngq6_paper_trade_identity_guard_v1();
"""

BACKFILL = """
update trades
set
    strategy = case
        when coalesce(strategy, '') in ('', 'UNKNOWN', 'UNKNOWN_STRATEGY')
        then 'NG_CONSERVATIVE_BREAKOUT_M1'
        else strategy
    end,
    timeframe = case
        when coalesce(timeframe, '') in ('', 'LIVE', 'UNKNOWN', 'UNKNOWN_TIMEFRAME')
        then 'M1'
        else timeframe
    end
where symbol = 'NGQ6@RTSX'
  and coalesce(trade_source, '') = 'paper'
  and coalesce(origin, 'paper') = 'paper'
  and (
       coalesce(strategy, '') in ('', 'UNKNOWN', 'UNKNOWN_STRATEGY')
    or coalesce(timeframe, '') in ('', 'LIVE', 'UNKNOWN', 'UNKNOWN_TIMEFRAME')
  );
"""

REPORT = """
select
    count(*) filter (
        where symbol='NGQ6@RTSX'
          and coalesce(trade_source,'')='paper'
          and coalesce(origin,'paper')='paper'
    ) as ngq6_paper_trades,
    count(*) filter (
        where symbol='NGQ6@RTSX'
          and coalesce(trade_source,'')='paper'
          and coalesce(origin,'paper')='paper'
          and strategy='NG_CONSERVATIVE_BREAKOUT_M1'
          and timeframe='M1'
    ) as ngq6_m1_identity_trades,
    count(*) filter (
        where symbol='NGQ6@RTSX'
          and coalesce(trade_source,'')='paper'
          and coalesce(origin,'paper')='paper'
          and (
               coalesce(strategy,'') in ('', 'UNKNOWN', 'UNKNOWN_STRATEGY')
            or coalesce(timeframe,'') in ('', 'LIVE', 'UNKNOWN', 'UNKNOWN_TIMEFRAME')
          )
    ) as ngq6_bad_identity_trades
from trades;
"""

RECENT = """
select
    id,
    created_at,
    symbol,
    strategy,
    timeframe,
    side,
    origin,
    trade_source,
    qty,
    price
from trades
where symbol='NGQ6@RTSX'
order by created_at desc
limit 10;
"""


def main() -> int:
    print("=== NGQ6 M1 TRADE IDENTITY FIX V1 ===")
    print("mode=apply_identity_guard")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(BACKFILL)
            updated = cur.rowcount

            cur.execute(REPORT)
            report = cur.fetchone()

            cur.execute(RECENT)
            recent = cur.fetchall()

        conn.commit()

    print(f"NGQ6_IDENTITY_BACKFILL_UPDATED rows={updated}")
    print(
        "NGQ6_IDENTITY_SUMMARY "
        f"ngq6_paper_trades={report['ngq6_paper_trades']} "
        f"ngq6_m1_identity_trades={report['ngq6_m1_identity_trades']} "
        f"ngq6_bad_identity_trades={report['ngq6_bad_identity_trades']}"
    )

    for r in recent:
        print(
            "NGQ6_RECENT_TRADE "
            f"id={r['id']} "
            f"created_at={r['created_at']} "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"side={r['side']} "
            f"origin={r['origin']} "
            f"trade_source={r['trade_source']} "
            f"qty={r['qty']} "
            f"price={r['price']}"
        )

    if int(report["ngq6_bad_identity_trades"] or 0) != 0:
        raise SystemExit("FAIL: NGQ6 bad identity trades remain")

    print("NGQ6_M1_TRADE_IDENTITY_FIX_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
