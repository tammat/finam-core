#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
from psycopg2.extras import RealDictCursor


EDGE_SQL = """
with last_day as (
    select max(created_at::date) as trade_date
    from trades
),
base as (
    select
        t.*
    from trades t
    join last_day d on t.created_at::date = d.trade_date
    where t.trade_source = 'paper'
      and t.is_invalid = false
),
agg as (
    select
        coalesce(nullif(strategy, ''), 'UNKNOWN') as strategy,
        coalesce(nullif(timeframe, ''), 'UNKNOWN') as timeframe,
        coalesce(nullif(continuous_symbol, ''), symbol) as continuous_symbol,
        count(*) as trades,
        count(distinct symbol) as symbols,
        sum(case when upper(side) = 'BUY' then qty else 0 end) as buy_qty,
        sum(case when upper(side) = 'SELL' then qty else 0 end) as sell_qty,
        sum(case when upper(side) = 'BUY' then qty * price else 0 end) as buy_value,
        sum(case when upper(side) = 'SELL' then qty * price else 0 end) as sell_value,
        sum(coalesce(commission, 0)) as commission
    from base
    group by
        coalesce(nullif(strategy, ''), 'UNKNOWN'),
        coalesce(nullif(timeframe, ''), 'UNKNOWN'),
        coalesce(nullif(continuous_symbol, ''), symbol)
),
scored as (
    select
        *,
        buy_qty - sell_qty as net_qty,
        sell_value - buy_value as gross_pnl,
        sell_value - buy_value - commission as net_pnl,
        case
            when trades > 0 then (sell_value - buy_value - commission) / trades
            else null
        end as net_pnl_per_trade,
        case
            when abs(sell_value - buy_value) > 0 then commission / abs(sell_value - buy_value)
            else null
        end as commission_drag
    from agg
)
select
    strategy,
    timeframe,
    continuous_symbol,
    symbols,
    trades,
    net_qty,
    gross_pnl,
    commission,
    net_pnl,
    net_pnl_per_trade,
    commission_drag
from scored
order by strategy, timeframe, continuous_symbol;
"""


RUNTIME_TABLES_SQL = """
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in (
      'runtime_active_universe',
      'runtime_strategy_quarantine',
      'runtime_strategy_actions',
      'runtime_disabled_strategies'
  )
order by table_name;
"""


def fmt(value: object, digits: int = 6) -> str:
    if value is None:
        return "None"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def decide_plan(row: dict) -> tuple[str, str, str, str]:
    strategy = row["strategy"]
    timeframe = row["timeframe"]
    net_qty = float(row["net_qty"] or 0)
    gross_pnl = float(row["gross_pnl"] or 0)
    net_pnl = float(row["net_pnl"] or 0)
    commission_drag = row["commission_drag"]
    commission_drag_value = float(commission_drag) if commission_drag is not None else None

    if strategy == "USDRUB_REGIME":
        return (
            "QUARANTINE_RUNTIME_CANDIDATE",
            "edge_negative_day",
            "runtime_active_universe",
            "disable_or_set_runtime_allowed_false_after_manual_review",
        )

    if strategy == "BR_CONSERVATIVE_BREAKOUT":
        if gross_pnl > 0 and net_pnl <= 0:
            return (
                "RESEARCH_ONLY_COMMISSION_DRAG",
                "gross_positive_but_commission_kills_edge",
                "strategy_parameters",
                "reduce_frequency_or_increase_target_before_runtime",
            )

        return (
            "RESEARCH_ONLY",
            "br_edge_not_confirmed",
            "strategy_parameters",
            "keep_in_research_until_multi_day_positive",
        )

    if strategy == "NG_CONSERVATIVE_BREAKOUT_M1":
        if net_qty != 0:
            return (
                "REQUIRE_MTM_FOR_OPEN_TAIL",
                "open_tail_requires_mark_to_market",
                "runtime_positions_or_mtm",
                "resolve_open_tail_before_edge_decision",
            )

        if net_pnl > -0.05:
            return (
                "KEEP_IN_RESEARCH_EDGE_WEAK",
                "near_flat_closed_result",
                "research_accumulation",
                "continue_paper_accumulation",
            )

        return (
            "RESEARCH_ONLY",
            "ng_edge_not_confirmed",
            "research_accumulation",
            "continue_paper_accumulation",
        )

    if net_qty != 0:
        return (
            "REQUIRE_MTM_FOR_OPEN_TAIL",
            "open_tail_requires_mark_to_market",
            "runtime_positions_or_mtm",
            "resolve_open_tail_before_edge_decision",
        )

    if net_pnl < 0:
        return (
            "RESEARCH_ONLY_NEGATIVE_EDGE",
            "net_negative",
            "research_accumulation",
            "do_not_promote_to_runtime",
        )

    if commission_drag_value is not None and commission_drag_value > 1.0:
        return (
            "RESEARCH_ONLY_COMMISSION_DRAG",
            "commission_drag_above_1",
            "strategy_parameters",
            "reduce_frequency_or_increase_target_before_runtime",
        )

    return (
        "KEEP_IN_RESEARCH",
        "no_runtime_promotion_rule_met",
        "research_accumulation",
        "continue_observation",
    )


def main() -> int:
    dsn = os.getenv("DATABASE_URL", "dbname=finam_core user=postgres")

    print("=== RUNTIME STRATEGY QUARANTINE PLAN V1 ===")
    print("mode=plan_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")

    action_counts: dict[str, int] = {}
    runtime_tables: list[str] = []

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(RUNTIME_TABLES_SQL)
            runtime_tables = [row["table_name"] for row in cur.fetchall()]

            print()
            print("RUNTIME_PLAN_DB_TABLES")
            if runtime_tables:
                for table in runtime_tables:
                    print(f"RUNTIME_TABLE_FOUND table={table}")
            else:
                print("RUNTIME_TABLE_FOUND none")

            cur.execute(EDGE_SQL)
            rows = cur.fetchall()

            print()
            print("RUNTIME_STRATEGY_QUARANTINE_PLAN_ROWS")

            for row in rows:
                action, reason, target, proposed_change = decide_plan(row)
                action_counts[action] = action_counts.get(action, 0) + 1

                print(
                    "RUNTIME_PLAN_ROW "
                    f"strategy={row['strategy']} "
                    f"timeframe={row['timeframe']} "
                    f"continuous_symbol={row['continuous_symbol']} "
                    f"symbols={row['symbols']} "
                    f"trades={row['trades']} "
                    f"net_qty={fmt(row['net_qty'], 4)} "
                    f"gross_pnl={fmt(row['gross_pnl'])} "
                    f"commission={fmt(row['commission'])} "
                    f"net_pnl={fmt(row['net_pnl'])} "
                    f"net_pnl_per_trade={fmt(row['net_pnl_per_trade'])} "
                    f"commission_drag={fmt(row['commission_drag'])} "
                    f"action={action} "
                    f"reason={reason} "
                    f"target={target} "
                    f"proposed_change={proposed_change}"
                )

    quarantine_count = action_counts.get("QUARANTINE_RUNTIME_CANDIDATE", 0)
    mtm_count = action_counts.get("REQUIRE_MTM_FOR_OPEN_TAIL", 0)
    commission_drag_count = action_counts.get("RESEARCH_ONLY_COMMISSION_DRAG", 0)

    print()
    print("RUNTIME_STRATEGY_QUARANTINE_PLAN_SUMMARY")
    print(f"rows={sum(action_counts.values())}")
    print(f"quarantine_runtime_candidates={quarantine_count}")
    print(f"mtm_required={mtm_count}")
    print(f"commission_drag_research_only={commission_drag_count}")
    print(f"runtime_tables_found={len(runtime_tables)}")

    for action in sorted(action_counts):
        print(f"ACTION_COUNT {action}={action_counts[action]}")

    if quarantine_count > 0 or mtm_count > 0 or commission_drag_count > 0:
        print("VERDICT=RUNTIME_STRATEGY_QUARANTINE_PLAN_RESTRICTIVE")
    else:
        print("VERDICT=RUNTIME_STRATEGY_QUARANTINE_PLAN_RESEARCH_ONLY")

    print("RUNTIME_STRATEGY_QUARANTINE_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
