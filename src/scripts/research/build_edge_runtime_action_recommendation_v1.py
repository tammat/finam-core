#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
from psycopg2.extras import RealDictCursor


STRATEGY_SQL = """
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
        sum(coalesce(commission, 0)) as commission,
        min(created_at) as first_trade,
        max(created_at) as last_trade
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
    buy_qty,
    sell_qty,
    net_qty,
    gross_pnl,
    commission,
    net_pnl,
    net_pnl_per_trade,
    commission_drag,
    first_trade,
    last_trade
from scored
order by
    case when net_qty = 0 then 0 else 1 end,
    net_pnl asc,
    strategy,
    timeframe;
"""


def fmt(value: object, digits: int = 6) -> str:
    if value is None:
        return "None"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def decide_action(row: dict) -> tuple[str, str, str]:
    strategy = row["strategy"]
    trades = int(row["trades"] or 0)
    net_qty = float(row["net_qty"] or 0)
    gross_pnl = float(row["gross_pnl"] or 0)
    net_pnl = float(row["net_pnl"] or 0)
    commission_drag = row["commission_drag"]
    commission_drag_value = float(commission_drag) if commission_drag is not None else None

    if strategy == "UNKNOWN":
        return (
            "BLOCK_RUNTIME_DECISION",
            "strategy_unknown_after_backfill",
            "Запретить runtime-решение до восстановления strategy.",
        )

    if net_qty != 0:
        return (
            "REQUIRE_MTM_FOR_OPEN_TAIL",
            "open_tail_requires_mark_to_market",
            "Не делать вывод по edge до MTM/закрытия хвоста.",
        )

    if net_pnl < 0 and gross_pnl < 0:
        return (
            "QUARANTINE_RUNTIME",
            "gross_and_net_negative",
            "Убрать из runtime-кандидатов до переработки сигнала.",
        )

    if gross_pnl > 0 and net_pnl <= 0:
        return (
            "RESEARCH_ONLY_COMMISSION_DRAG",
            "gross_positive_but_commission_kills_edge",
            "Оставить в research; снизить частоту или увеличить target/expected move.",
        )

    if net_pnl <= -0.05:
        return (
            "QUARANTINE_RUNTIME",
            "net_negative_material",
            "Убрать из runtime-кандидатов до повторной проверки.",
        )

    if trades < 20:
        return (
            "KEEP_IN_RESEARCH_LOW_SAMPLE",
            "sample_too_small",
            "Оставить в accumulation; данных мало для runtime.",
        )

    if commission_drag_value is not None and commission_drag_value > 1.0:
        return (
            "RESEARCH_ONLY_COMMISSION_DRAG",
            "commission_drag_above_1",
            "Проверить экономику исполнения и размер цели.",
        )

    if net_pnl > 0:
        return (
            "KEEP_IN_RESEARCH_CANDIDATE",
            "positive_day_requires_more_days",
            "Не включать real; продолжить accumulation несколько дней.",
        )

    return (
        "KEEP_IN_RESEARCH",
        "no_strong_signal",
        "Оставить в research без runtime promotion.",
    )


def main() -> int:
    dsn = os.getenv("DATABASE_URL", "dbname=finam_core user=postgres")

    print("=== EDGE RUNTIME ACTION RECOMMENDATION V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")

    actions: list[str] = []
    blockers = 0
    quarantines = 0
    mtm_required = 0
    research_only = 0
    keep_research = 0

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(STRATEGY_SQL)
            rows = cur.fetchall()

            print()
            print("EDGE_RUNTIME_ACTION_ROWS")

            for row in rows:
                action, reason, recommendation = decide_action(row)
                actions.append(action)

                if action == "BLOCK_RUNTIME_DECISION":
                    blockers += 1
                elif action == "QUARANTINE_RUNTIME":
                    quarantines += 1
                elif action == "REQUIRE_MTM_FOR_OPEN_TAIL":
                    mtm_required += 1
                elif action.startswith("RESEARCH_ONLY"):
                    research_only += 1
                elif action.startswith("KEEP_IN_RESEARCH"):
                    keep_research += 1

                print(
                    "EDGE_ACTION_ROW "
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
                    f"recommendation={recommendation}"
                )

    print()
    print("EDGE_RUNTIME_ACTION_SUMMARY")
    print(f"rows={len(actions)}")
    print(f"blockers={blockers}")
    print(f"quarantines={quarantines}")
    print(f"mtm_required={mtm_required}")
    print(f"research_only={research_only}")
    print(f"keep_research={keep_research}")

    if blockers > 0:
        print("VERDICT=EDGE_RUNTIME_ACTION_BLOCKED_BY_UNKNOWN_CONTEXT")
    elif quarantines > 0 or mtm_required > 0 or research_only > 0:
        print("VERDICT=EDGE_RUNTIME_ACTION_RESTRICTIVE")
    else:
        print("VERDICT=EDGE_RUNTIME_ACTION_KEEP_RESEARCH_ONLY")

    print("EDGE_RUNTIME_ACTION_RECOMMENDATION_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
