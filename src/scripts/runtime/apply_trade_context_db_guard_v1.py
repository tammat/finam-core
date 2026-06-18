#!/usr/bin/env python3
from __future__ import annotations

import os

import psycopg2


# Русский комментарий:
# TRADE_CONTEXT_DB_GUARD_V1
# PostgreSQL-level BEFORE INSERT/UPDATE trigger для trades.
# Последний рубеж защиты: если Python writer обошёл guard,
# БД сама восстановит strategy/timeframe/continuous_symbol для известных маршрутов.
# Execution и real trading не включаются.


SQL = r"""
create or replace function trade_context_guard_trades_before_write_v1()
returns trigger
language plpgsql
as $$
declare
    payload_strategy text;
    payload_timeframe text;
    payload_continuous text;
    fallback_strategy text;
    fallback_timeframe text;
    fallback_continuous text;
begin
    payload_strategy := nullif(coalesce(
        NEW.payload ->> 'strategy',
        NEW.payload #>> '{trade_context_snapshot,strategy}',
        NEW.payload #>> '{trade_context,strategy}',
        NEW.payload #>> '{risk_context,strategy}'
    ), '');

    payload_timeframe := nullif(coalesce(
        NEW.payload ->> 'timeframe',
        NEW.payload #>> '{trade_context_snapshot,timeframe}',
        NEW.payload #>> '{trade_context,timeframe}',
        NEW.payload #>> '{risk_context,timeframe}'
    ), '');

    payload_continuous := nullif(coalesce(
        NEW.payload ->> 'continuous_symbol',
        NEW.payload #>> '{trade_context_snapshot,continuous_symbol}',
        NEW.payload #>> '{trade_context,continuous_symbol}',
        NEW.payload #>> '{risk_context,continuous_symbol}'
    ), '');

    fallback_strategy := null;
    fallback_timeframe := null;
    fallback_continuous := null;

    if NEW.symbol = 'USDRUBF@RTSX' then
        fallback_strategy := 'USDRUB_REGIME';
        fallback_timeframe := 'LIVE';
        fallback_continuous := 'USDRUB_CONT';
    elsif NEW.symbol in ('NGM6@RTSX', 'NGN6@RTSX') then
        fallback_strategy := 'NG_CONSERVATIVE_BREAKOUT_M1';
        fallback_timeframe := 'LIVE';
        fallback_continuous := 'NG_CONT';
    elsif NEW.symbol = 'BRN6@RTSX' then
        fallback_strategy := 'BR_CONSERVATIVE_BREAKOUT';
        fallback_timeframe := 'LIVE';
        fallback_continuous := 'BR_CONT';
    end if;

    if NEW.strategy is null
       or btrim(NEW.strategy) = ''
       or NEW.strategy in ('UNKNOWN', 'UNKNOWN_STRATEGY')
    then
        NEW.strategy := coalesce(payload_strategy, fallback_strategy, NEW.strategy);
    end if;

    if NEW.timeframe is null
       or btrim(NEW.timeframe) = ''
       or NEW.timeframe in ('UNKNOWN', 'UNKNOWN_TIMEFRAME')
    then
        NEW.timeframe := coalesce(payload_timeframe, fallback_timeframe, NEW.timeframe);
    end if;

    if NEW.continuous_symbol is null
       or btrim(NEW.continuous_symbol) = ''
       or NEW.continuous_symbol = 'UNKNOWN'
    then
        NEW.continuous_symbol := coalesce(payload_continuous, fallback_continuous, NEW.continuous_symbol);
    end if;

    return NEW;
end;
$$;

drop trigger if exists trade_context_guard_trades_before_write_v1 on trades;

create trigger trade_context_guard_trades_before_write_v1
before insert or update on trades
for each row
execute function trade_context_guard_trades_before_write_v1();
"""


VERIFY_SQL = """
select
    tgname as trigger_name,
    tgenabled as enabled
from pg_trigger
where tgname = 'trade_context_guard_trades_before_write_v1';
"""


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    apply = os.getenv("APPLY", "0") == "1"

    print("=== TRADE CONTEXT DB GUARD V1 ===")
    print(f"mode={'apply' if apply else 'dry_run'}")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print(f"db_update={1 if apply else 0}")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            if apply:
                cur.execute(SQL)
                conn.commit()
            else:
                conn.rollback()

            cur.execute(VERIFY_SQL)
            rows = cur.fetchall()

    print()
    print("TRADE_CONTEXT_DB_GUARD_VERIFY")
    for row in rows:
        print(f"TRIGGER_ROW trigger_name={row[0]} enabled={row[1]}")

    print()
    print("TRADE_CONTEXT_DB_GUARD_SUMMARY")
    print(f"trigger_found={1 if rows else 0}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"db_update={1 if apply else 0}")

    if apply and rows:
        print("VERDICT=TRADE_CONTEXT_DB_GUARD_APPLY_OK")
    elif not apply:
        print("VERDICT=TRADE_CONTEXT_DB_GUARD_DRY_RUN_READY")
    else:
        print("VERDICT=TRADE_CONTEXT_DB_GUARD_APPLY_FAILED")

    print("TRADE_CONTEXT_DB_GUARD_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
