#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2


DDL = """
create table if not exists research_closed_trades_quarantine (
    trade_id bigint primary key,
    symbol text,
    strategy text,
    timeframe text,
    side text,
    net_pnl numeric,
    entry_price numeric,
    exit_price numeric,
    hold_seconds numeric,
    source text,
    trade_source text,
    exit_reason text,

    quarantine_reason text not null,
    severity text not null,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_research_closed_trades_quarantine_symbol
    on research_closed_trades_quarantine(symbol);

create index if not exists idx_research_closed_trades_quarantine_reason
    on research_closed_trades_quarantine(quarantine_reason);

create index if not exists idx_research_closed_trades_quarantine_severity
    on research_closed_trades_quarantine(severity);
"""


def conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def main() -> None:
    print("=== CLOSED TRADES DATA QUARANTINE V1 ===")
    print("mode=research_only")
    print("delete_rows=0")
    print("mutate_closed_trades=0")
    print()

    sql = """
        with base as (
            select
                id as trade_id,
                symbol,
                coalesce(nullif(strategy,''),'unknown') as strategy,
                coalesce(nullif(timeframe,''),'unknown') as timeframe,
                side,
                net_pnl,
                entry_price,
                exit_price,
                extract(epoch from (
                    coalesce(closed_at, exit_ts, created_at)
                    -
                    coalesce(opened_at, entry_ts, created_at)
                )) as hold_seconds,
                source,
                trade_source,
                coalesce(
                    payload->>'exit_reason',
                    payload->'exit_payload'->>'exit_reason',
                    payload->'exit_payload'->>'reason',
                    payload->>'reason',
                    'UNKNOWN'
                ) as exit_reason
            from closed_trades
            where net_pnl is not null
        ),
        flagged as (
            select
                *,
                array_remove(array[
                    case when strategy='unknown' then 'strategy_unknown' end,
                    case when timeframe='unknown' then 'timeframe_unknown' end,
                    case when exit_reason='UNKNOWN' then 'exit_reason_unknown' end,
                    case when exit_price is null then 'exit_price_missing' end,
                    case when entry_price is null then 'entry_price_missing' end,
                    case when exit_price <= 0 then 'exit_price_non_positive' end,
                    case when entry_price <= 0 then 'entry_price_non_positive' end,
                    case when source='closed_trade_engine_v1' then 'legacy_closed_trade_engine_v1' end,
                    case when hold_seconds < 300 and net_pnl < -100 then 'short_hold_large_loss' end,
                    case when symbol in ('PLZL@MISX','LKOH@MISX','OZON@MISX')
                           and strategy='unknown'
                           and exit_reason='UNKNOWN'
                           and net_pnl < -100
                         then 'catastrophic_unknown_equity_loss' end
                ], null) as reasons
            from base
        )
        select
            trade_id,
            symbol,
            strategy,
            timeframe,
            side,
            net_pnl,
            entry_price,
            exit_price,
            hold_seconds,
            source,
            trade_source,
            exit_reason,
            array_to_string(reasons, '|') as quarantine_reason,
            case
                when 'exit_price_non_positive' = any(reasons) then 'CRITICAL'
                when 'catastrophic_unknown_equity_loss' = any(reasons) then 'CRITICAL'
                when 'short_hold_large_loss' = any(reasons) then 'HIGH'
                when array_length(reasons, 1) >= 3 then 'HIGH'
                else 'MEDIUM'
            end as severity
        from flagged
        where array_length(reasons, 1) is not null;
    """

    upsert = """
        insert into research_closed_trades_quarantine (
            trade_id,
            symbol,
            strategy,
            timeframe,
            side,
            net_pnl,
            entry_price,
            exit_price,
            hold_seconds,
            source,
            trade_source,
            exit_reason,
            quarantine_reason,
            severity,
            updated_at
        )
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
        on conflict (trade_id)
        do update set
            symbol=excluded.symbol,
            strategy=excluded.strategy,
            timeframe=excluded.timeframe,
            side=excluded.side,
            net_pnl=excluded.net_pnl,
            entry_price=excluded.entry_price,
            exit_price=excluded.exit_price,
            hold_seconds=excluded.hold_seconds,
            source=excluded.source,
            trade_source=excluded.trade_source,
            exit_reason=excluded.exit_reason,
            quarantine_reason=excluded.quarantine_reason,
            severity=excluded.severity,
            updated_at=now()
    """

    with conn() as c:
        with c.cursor() as cur:
            cur.execute(DDL)
            cur.execute(sql)
            rows = cur.fetchall()

            for row in rows:
                cur.execute(upsert, row)

            cur.execute("""
                delete from research_closed_trades_quarantine q
                where not exists (
                    select 1 from closed_trades ct
                    where ct.id = q.trade_id
                );
            """)

            cur.execute("""
                select count(*) from closed_trades where net_pnl is not null;
            """)
            total_closed = int(cur.fetchone()[0] or 0)

            cur.execute("""
                select count(*) from research_closed_trades_quarantine;
            """)
            total_quarantine = int(cur.fetchone()[0] or 0)

            cur.execute("""
                select severity, count(*)
                from research_closed_trades_quarantine
                group by severity
                order by severity;
            """)
            by_severity = cur.fetchall()

            cur.execute("""
                select symbol, count(*) as rows, sum(net_pnl) as net_pnl
                from research_closed_trades_quarantine
                group by symbol
                order by rows desc, symbol
                limit 20;
            """)
            by_symbol = cur.fetchall()

            cur.execute("""
                select quarantine_reason, count(*) as rows
                from research_closed_trades_quarantine
                group by quarantine_reason
                order by rows desc
                limit 30;
            """)
            by_reason = cur.fetchall()

    rate = 0 if total_closed == 0 else total_quarantine / total_closed

    print(f"TOTAL_CLOSED_TRADES={total_closed}")
    print(f"QUARANTINED_TRADES={total_quarantine}")
    print(f"QUARANTINE_RATE={rate:.4f}")

    print()
    print("BY_SEVERITY")
    for severity, rows_count in by_severity:
        print(f"SEVERITY_ROW severity={severity} rows={rows_count}")

    print()
    print("BY_SYMBOL")
    for symbol, rows_count, net_pnl in by_symbol:
        print(
            f"SYMBOL_ROW symbol={symbol} rows={rows_count} "
            f"net_pnl={float(net_pnl or 0):.8f}"
        )

    print()
    print("BY_REASON")
    for reason, rows_count in by_reason:
        print(f"REASON_ROW reason={reason} rows={rows_count}")

    print()
    print(f"ROWS_WRITTEN={total_quarantine}")
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
