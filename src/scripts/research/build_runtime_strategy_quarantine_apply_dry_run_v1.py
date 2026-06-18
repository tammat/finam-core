#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
from psycopg2.extras import RealDictCursor


EDGE_PLAN_SQL = """
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


TABLE_COLUMNS_SQL = """
select column_name
from information_schema.columns
where table_schema = 'public'
  and table_name = 'runtime_active_universe'
order by ordinal_position;
"""


RUNTIME_ROWS_SQL = """
select *
from runtime_active_universe
order by 1;
"""


def fmt(value: object, digits: int = 6) -> str:
    if value is None:
        return "None"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def decide_action(row: dict) -> tuple[str, str, str]:
    strategy = normalize_text(row.get("strategy"))
    net_qty = float(row.get("net_qty") or 0)
    gross_pnl = float(row.get("gross_pnl") or 0)
    net_pnl = float(row.get("net_pnl") or 0)

    if strategy == "USDRUB_REGIME":
        return (
            "QUARANTINE_RUNTIME_CANDIDATE",
            "edge_negative_day",
            "set_runtime_disabled_or_research_only",
        )

    if strategy == "BR_CONSERVATIVE_BREAKOUT":
        if gross_pnl > 0 and net_pnl <= 0:
            return (
                "RESEARCH_ONLY_COMMISSION_DRAG",
                "gross_positive_but_commission_kills_edge",
                "keep_runtime_disabled_research_only",
            )
        return (
            "RESEARCH_ONLY",
            "br_edge_not_confirmed",
            "keep_runtime_disabled_research_only",
        )

    if strategy == "NG_CONSERVATIVE_BREAKOUT_M1":
        if net_qty != 0:
            return (
                "REQUIRE_MTM_FOR_OPEN_TAIL",
                "open_tail_requires_mark_to_market",
                "no_runtime_change_until_mtm",
            )
        return (
            "KEEP_RESEARCH_ACCUMULATION",
            "near_flat_or_unconfirmed",
            "continue_paper_accumulation",
        )

    if net_qty != 0:
        return (
            "REQUIRE_MTM_FOR_OPEN_TAIL",
            "open_tail_requires_mark_to_market",
            "no_runtime_change_until_mtm",
        )

    if net_pnl < 0:
        return (
            "RESEARCH_ONLY_NEGATIVE_EDGE",
            "net_negative",
            "keep_runtime_disabled_research_only",
        )

    return (
        "KEEP_RESEARCH",
        "no_runtime_promotion_rule_met",
        "continue_observation",
    )


def find_runtime_matches(runtime_rows: list[dict], plan_row: dict) -> list[dict]:
    strategy = normalize_text(plan_row.get("strategy"))
    continuous_symbol = normalize_text(plan_row.get("continuous_symbol"))
    timeframe = normalize_text(plan_row.get("timeframe"))

    matches: list[dict] = []

    for row in runtime_rows:
        values = {k: normalize_text(v) for k, v in row.items()}

        row_text = " ".join(values.values())

        strategy_match = strategy and strategy in row_text
        symbol_match = continuous_symbol and continuous_symbol in row_text
        timeframe_match = timeframe and timeframe in row_text

        # Русский комментарий:
        # runtime_active_universe в проекте мог эволюционировать по схеме.
        # Поэтому dry-run использует мягкое сопоставление по тексту строки:
        # strategy + continuous_symbol, а timeframe учитывается как дополнительное подтверждение.
        if strategy_match and symbol_match:
            row_copy = dict(row)
            row_copy["_timeframe_match"] = timeframe_match
            matches.append(row_copy)

    return matches


def runtime_identity(row: dict) -> str:
    keys = [
        "id",
        "symbol",
        "continuous_symbol",
        "strategy",
        "timeframe",
        "is_enabled",
        "runtime_allowed",
        "execution_enabled",
        "status",
    ]

    parts = []
    for key in keys:
        if key in row:
            parts.append(f"{key}={row.get(key)}")

    if parts:
        return ";".join(parts)

    return ";".join(f"{key}={value}" for key, value in row.items())


def main() -> int:
    dsn = os.getenv("DATABASE_URL", "dbname=finam_core user=postgres")

    print("=== RUNTIME STRATEGY QUARANTINE APPLY DRY RUN V1 ===")
    print("mode=dry_run")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("apply=0")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(TABLE_COLUMNS_SQL)
            columns = [row["column_name"] for row in cur.fetchall()]

            if not columns:
                print("RUNTIME_ACTIVE_UNIVERSE_FOUND=0")
                print("VERDICT=RUNTIME_STRATEGY_QUARANTINE_APPLY_DRY_RUN_BLOCKED_NO_TABLE")
                return 1

            print("RUNTIME_ACTIVE_UNIVERSE_FOUND=1")
            print("RUNTIME_ACTIVE_UNIVERSE_COLUMNS=" + ",".join(columns))

            cur.execute(RUNTIME_ROWS_SQL)
            runtime_rows = [dict(row) for row in cur.fetchall()]

            print(f"RUNTIME_ACTIVE_UNIVERSE_ROWS={len(runtime_rows)}")

            cur.execute(EDGE_PLAN_SQL)
            plan_rows = [dict(row) for row in cur.fetchall()]

    planned_changes = 0
    unmatched = 0
    quarantine_candidates = 0
    research_only = 0
    mtm_required = 0

    print()
    print("RUNTIME_STRATEGY_QUARANTINE_APPLY_DRY_RUN_ROWS")

    for plan in plan_rows:
        action, reason, proposed_change = decide_action(plan)

        if action == "QUARANTINE_RUNTIME_CANDIDATE":
            quarantine_candidates += 1
        elif action.startswith("RESEARCH_ONLY"):
            research_only += 1
        elif action == "REQUIRE_MTM_FOR_OPEN_TAIL":
            mtm_required += 1

        matches = find_runtime_matches(runtime_rows, plan)

        if not matches:
            unmatched += 1
            print(
                "RUNTIME_DRY_RUN_ROW "
                f"strategy={plan['strategy']} "
                f"timeframe={plan['timeframe']} "
                f"continuous_symbol={plan['continuous_symbol']} "
                f"trades={plan['trades']} "
                f"net_qty={fmt(plan['net_qty'], 4)} "
                f"gross_pnl={fmt(plan['gross_pnl'])} "
                f"commission={fmt(plan['commission'])} "
                f"net_pnl={fmt(plan['net_pnl'])} "
                f"commission_drag={fmt(plan['commission_drag'])} "
                f"action={action} "
                f"reason={reason} "
                f"runtime_match=0 "
                f"would_update=0 "
                f"proposed_change={proposed_change}"
            )
            continue

        for match in matches:
            # Русский комментарий:
            # На этом этапе ничего не обновляем. would_update=1 означает только,
            # что строка runtime_active_universe найдена и попадает под план.
            would_update = action in {
                "QUARANTINE_RUNTIME_CANDIDATE",
                "RESEARCH_ONLY_COMMISSION_DRAG",
                "RESEARCH_ONLY",
                "RESEARCH_ONLY_NEGATIVE_EDGE",
            }

            if would_update:
                planned_changes += 1

            print(
                "RUNTIME_DRY_RUN_ROW "
                f"strategy={plan['strategy']} "
                f"timeframe={plan['timeframe']} "
                f"continuous_symbol={plan['continuous_symbol']} "
                f"trades={plan['trades']} "
                f"net_qty={fmt(plan['net_qty'], 4)} "
                f"gross_pnl={fmt(plan['gross_pnl'])} "
                f"commission={fmt(plan['commission'])} "
                f"net_pnl={fmt(plan['net_pnl'])} "
                f"commission_drag={fmt(plan['commission_drag'])} "
                f"action={action} "
                f"reason={reason} "
                f"runtime_match=1 "
                f"timeframe_match={int(bool(match.get('_timeframe_match')))} "
                f"would_update={int(would_update)} "
                f"proposed_change={proposed_change} "
                f"runtime_row={runtime_identity(match)}"
            )

    print()
    print("RUNTIME_STRATEGY_QUARANTINE_APPLY_DRY_RUN_SUMMARY")
    print(f"plan_rows={len(plan_rows)}")
    print(f"runtime_rows={len(runtime_rows)}")
    print(f"planned_changes={planned_changes}")
    print(f"unmatched_plan_rows={unmatched}")
    print(f"quarantine_candidates={quarantine_candidates}")
    print(f"research_only={research_only}")
    print(f"mtm_required={mtm_required}")
    print("apply=0")

    print("VERDICT=RUNTIME_STRATEGY_QUARANTINE_APPLY_DRY_RUN_READY")
    print("RUNTIME_STRATEGY_QUARANTINE_APPLY_DRY_RUN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
