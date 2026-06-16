#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SYMBOL = "SBER@MISX"
STRATEGY = "MOEX_SIMPLE_MOMENTUM"
TIMEFRAME = "D1"
SOURCE = "paper"

SQL_MAIN = """
select
    count(*) as trades,
    sum(a.pnl) as pnl,
    avg(a.pnl) as expectancy,
    count(*) filter (where a.pnl > 0)::numeric / nullif(count(*),0) as winrate,
    count(distinct c.entry_ts::date) as entry_days,
    count(distinct c.exit_ts::date) as exit_days,
    count(distinct c.exit_ts) as distinct_exit_ts,
    count(*) filter (where a.attribution_quality='FULL') as full_ctx,
    count(*) filter (where a.attribution_quality='PARTIAL') as partial_ctx,
    count(*) filter (where a.attribution_quality='RISK_CONTEXT_WEAK') as weak_ctx,
    min(c.entry_ts) as first_entry,
    max(c.exit_ts) as last_exit
from trade_attribution_v2 a
join closed_trade_chains_v2 c
  on c.id = a.closed_trade_id
where a.symbol=%s
  and a.strategy=%s
  and a.timeframe=%s
  and a.trade_source=%s;
"""

SQL_TABLE_EXISTS = """
select exists (
    select 1
    from information_schema.tables
    where table_schema='public'
      and table_name=%s
) as exists;
"""

SQL_WF_CANDIDATES = """
select table_name
from information_schema.tables
where table_schema='public'
  and table_name in (
      'strategy_walkforward',
      'strategy_walkforward_results',
      'strategy_walkforward_v1',
      'strategy_walkforward_v2'
  )
order by table_name;
"""

SQL_WF_TEMPLATE = """
select
    train_trades,
    test_trades,
    train_pf,
    test_pf,
    test_expectancy,
    stability_score,
    status,
    computed_at
from {table_name}
where symbol=%s
  and strategy=%s
  and timeframe=%s
order by computed_at desc
limit 1;
"""

def table_exists(cur, table_name: str) -> bool:
    cur.execute(SQL_TABLE_EXISTS, (table_name,))
    return bool(cur.fetchone()["exists"])

def load_walkforward(cur) -> dict:
    cur.execute(SQL_WF_CANDIDATES)
    candidates = [r["table_name"] for r in cur.fetchall()]

    for table_name in candidates:
        try:
            cur.execute(
                SQL_WF_TEMPLATE.format(table_name=table_name),
                (SYMBOL, STRATEGY, TIMEFRAME),
            )
            row = cur.fetchone()
            if row:
                result = dict(row)
                result["wf_table"] = table_name
                return result
        except Exception:
            continue

    return {
        "train_trades": 0,
        "test_trades": 0,
        "train_pf": 0,
        "test_pf": 0,
        "test_expectancy": 0,
        "stability_score": 0,
        "status": "NO_WALKFORWARD_TABLE",
        "wf_table": "",
    }

def verdict(row: dict, wf: dict) -> tuple[str, str]:
    trades = int(row["trades"] or 0)
    entry_days = int(row["entry_days"] or 0)
    exit_days = int(row["exit_days"] or 0)
    test_trades = int(wf["test_trades"] or 0)
    test_pf = float(wf["test_pf"] or 0)
    test_expectancy = float(wf["test_expectancy"] or 0)
    wf_status = str(wf["status"] or "")

    if trades < 100:
        return "RESEARCH_ONLY", "малая_общая_выборка"

    if entry_days < 10 or exit_days < 10:
        return "RESEARCH_ONLY", "низкая_временная_диверсификация"

    if wf_status == "NO_WALKFORWARD_TABLE":
        return "RUNTIME_SHADOW_ONLY", "нет_таблицы_walkforward_нужна_повторная_валидация"

    if wf_status != "OOS_CONFIRMED":
        return "RESEARCH_ONLY", f"walkforward_не_подтвержден:{wf_status}"

    if test_trades < 30:
        return "RUNTIME_SHADOW_ONLY", "малая_OOS_выборка"

    if test_pf <= 1.2 or test_expectancy <= 0:
        return "RUNTIME_SHADOW_ONLY", "слабый_OOS_edge"

    return "RUNTIME_SHADOW_ONLY", "кандидат_подтвержден_но_только_shadow_before_controlled_runtime"

def main() -> int:
    print("=== SBER D1 RUNTIME READINESS AUDIT V1 ===")
    print("mode=research_audit")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print(f"timeframe={TIMEFRAME}")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL_MAIN, (SYMBOL, STRATEGY, TIMEFRAME, SOURCE))
            row = dict(cur.fetchone())
            wf = load_walkforward(cur)

    status, reason = verdict(row, wf)

    print(
        "SBER_D1_READINESS_ROW "
        f"trades={int(row['trades'] or 0)} "
        f"pnl={float(row['pnl'] or 0):.4f} "
        f"expectancy={float(row['expectancy'] or 0):.6f} "
        f"winrate={float(row['winrate'] or 0):.4f} "
        f"entry_days={int(row['entry_days'] or 0)} "
        f"exit_days={int(row['exit_days'] or 0)} "
        f"distinct_exit_ts={int(row['distinct_exit_ts'] or 0)} "
        f"full_ctx={int(row['full_ctx'] or 0)} "
        f"partial_ctx={int(row['partial_ctx'] or 0)} "
        f"weak_ctx={int(row['weak_ctx'] or 0)} "
        f"train_trades={int(wf['train_trades'] or 0)} "
        f"test_trades={int(wf['test_trades'] or 0)} "
        f"train_pf={float(wf['train_pf'] or 0):.4f} "
        f"test_pf={float(wf['test_pf'] or 0):.4f} "
        f"test_expectancy={float(wf['test_expectancy'] or 0):.6f} "
        f"stability_score={float(wf['stability_score'] or 0):.4f} "
        f"wf_status={wf['status']} "
        f"wf_table={wf['wf_table']} "
        f"first_entry={row['first_entry']} "
        f"last_exit={row['last_exit']}"
    )

    print(
        "SBER_D1_RUNTIME_VERDICT "
        f"status={status} "
        f"reason={reason} "
        "runtime_allow=0 "
        "execution_enabled=0"
    )

    print("SBER_D1_RUNTIME_READINESS_AUDIT_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
