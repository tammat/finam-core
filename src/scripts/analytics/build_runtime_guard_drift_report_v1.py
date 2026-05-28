from __future__ import annotations

import os

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            with linked as (
              select
                r.signal_id,
                r.symbol,
                r.strategy,
                r.timeframe,
                r.guard_decision,
                r.runtime_soft_blocked,
                r.guard_matched,
                r.profit_factor as guard_pf,
                r.expectancy as guard_expectancy,
                r.ts as registry_ts,
                t.id as trade_id,
                t.fill_id,
                p.trade_pnl,
                case
                  when t.id is null then 'NO_TRADE'
                  when p.trade_pnl is null then 'NO_PNL'
                  when p.trade_pnl > 0 then 'WIN'
                  when p.trade_pnl < 0 then 'LOSS'
                  else 'FLAT'
                end as outcome_class
              from runtime_guard_signal_registry_v1 r
              left join trades t
                on t.payload->>'signal_id' = r.signal_id
              left join analytics_intraday_pnl p
                on p.trade_id = t.id
            ),
            grouped as (
              select
                symbol,
                strategy,
                timeframe,
                guard_decision,
                runtime_soft_blocked,
                count(*) as signals,
                count(*) filter (where guard_matched is true) as matched,
                count(*) filter (where outcome_class = 'NO_TRADE') as no_trade,
                count(*) filter (where outcome_class = 'NO_PNL') as no_pnl,
                count(*) filter (where outcome_class in ('WIN','LOSS','FLAT')) as closed,
                count(*) filter (where outcome_class = 'WIN') as wins,
                count(*) filter (where outcome_class = 'LOSS') as losses,
                count(*) filter (where outcome_class = 'FLAT') as flats,
                sum(trade_pnl) filter (where outcome_class in ('WIN','LOSS','FLAT')) as net_pnl,
                avg(trade_pnl) filter (where outcome_class in ('WIN','LOSS','FLAT')) as expectancy_realized,
                avg(guard_pf) as avg_guard_pf,
                avg(guard_expectancy) as avg_guard_expectancy,
                max(registry_ts) as last_ts
              from linked
              group by
                symbol,
                strategy,
                timeframe,
                guard_decision,
                runtime_soft_blocked
            )
            select
              *,
              case
                when closed = 0 then 'NO_OUTCOME_YET'
                when guard_decision = 'BLOCK' and net_pnl > 0 then 'FALSE_BLOCK_CANDIDATE'
                when guard_decision in ('ALLOW','WATCH') and net_pnl < 0 then 'FALSE_ALLOW_CANDIDATE'
                when guard_decision = 'BLOCK' and net_pnl <= 0 then 'BLOCK_CONFIRMED'
                when guard_decision in ('ALLOW','WATCH') and net_pnl >= 0 then 'ALLOW_CONFIRMED'
                else 'UNKNOWN'
              end as drift_status
            from grouped
            order by
              closed desc,
              signals desc,
              symbol,
              strategy;
            """)

            rows = cur.fetchall()

    print("RUNTIME_GUARD_DRIFT_REPORT_V1")

    for r in rows:
        print(
            "RUNTIME_GUARD_DRIFT_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"decision={r['guard_decision']} "
            f"soft_blocked={r['runtime_soft_blocked']} "
            f"signals={r['signals']} "
            f"matched={r['matched']} "
            f"no_trade={r['no_trade']} "
            f"no_pnl={r['no_pnl']} "
            f"closed={r['closed']} "
            f"wins={r['wins']} "
            f"losses={r['losses']} "
            f"net_pnl={r['net_pnl']} "
            f"realized_expectancy={r['expectancy_realized']} "
            f"guard_pf={r['avg_guard_pf']} "
            f"guard_expectancy={r['avg_guard_expectancy']} "
            f"drift_status={r['drift_status']} "
            f"last_ts={r['last_ts']}",
            flush=True,
        )

    print(f"RUNTIME_GUARD_DRIFT_REPORT_V1_OK rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
