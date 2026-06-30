#!/usr/bin/env python3
import os
import re
import psycopg
from psycopg.rows import dict_row

dsn = os.environ["DATABASE_URL"]

SOURCE_TABLES = [
    "analytics_futures_rs_bottom_paper_observation_v1",
    "analytics_rs_bottom_runtime_dry_run_v1",
    "trades",
]

def classify(value: str) -> str:
    v = (value or "").upper()
    if "BREAKOUT" in v:
        return "BREAKOUT"
    if "MEAN_REVERSION" in v or "REVERSION" in v:
        return "MEAN_REVERSION"
    if "MOMENTUM" in v or "IMPULSE" in v:
        return "MOMENTUM"
    if "TREND" in v:
        return "TREND_FOLLOWING"
    if "PULLBACK" in v or "RETEST" in v:
        return "PULLBACK"
    if "VOLATILITY" in v:
        return "VOLATILITY_EXPANSION"
    if "COMPRESSION" in v or "EXPANSION" in v:
        return "COMPRESSION_EXPANSION"
    if "REGIME" in v:
        return "REGIME_SWITCH"
    if "TIME_EXIT" in v:
        return "EXIT_LOGIC"
    return "UNKNOWN"

print("=== STRATEGY_CLASS_DISCOVERY_AUDIT_V1 ===")
print("mode=read_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

rows = []

with psycopg.connect(dsn, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        for table in SOURCE_TABLES:
            cur.execute("""
                select exists (
                    select 1
                    from information_schema.tables
                    where table_schema='public'
                      and table_name=%s
                ) as exists
            """, (table,))
            if not cur.fetchone()["exists"]:
                print(f"SOURCE_SKIP table={table} reason=missing")
                continue

            cur.execute("""
                select column_name
                from information_schema.columns
                where table_schema='public'
                  and table_name=%s
            """, (table,))
            cols = {r["column_name"] for r in cur.fetchall()}

            if "return_pct" in cols:
                pnl_col = "return_pct"
            elif "net_pnl" in cols:
                pnl_col = "net_pnl"
            elif "pnl" in cols:
                pnl_col = "pnl"
            else:
                print(f"SOURCE_SKIP table={table} reason=no_pnl_column")
                continue

            status_filter = ""
            if "status" in cols:
                status_filter = "and status in ('SUCCESS','FAILURE')"

            class_expr_parts = []
            for c in ["strategy_class", "signal_class", "strategy", "reason", "family", "symbol"]:
                if c in cols:
                    class_expr_parts.append(c)

            if not class_expr_parts:
                class_expr = "'UNKNOWN'"
            else:
                class_expr = "coalesce(" + ", ".join(class_expr_parts) + ", 'UNKNOWN')"

            sql = f"""
                select
                    %s as source_table,
                    {class_expr}::text as raw_class,
                    count(*)::int as completed,
                    count(*) filter (where {pnl_col} > 0)::int as wins,
                    count(*) filter (where {pnl_col} <= 0)::int as losses,
                    avg({pnl_col}) as expectancy,
                    sum({pnl_col}) as gross_pnl,
                    count(*) * 0.02 as fee_drag_estimate,
                    sum({pnl_col}) - count(*) * 0.02 as net_pnl_estimate,
                    case
                        when abs(sum(least({pnl_col},0))) > 0
                        then sum(greatest({pnl_col},0)) / abs(sum(least({pnl_col},0)))
                        else null
                    end as profit_factor
                from {table}
                where {pnl_col} is not null
                  {status_filter}
                group by raw_class
            """
            cur.execute(sql, (table,))
            rows.extend(cur.fetchall())

agg = {}
for r in rows:
    strategy_class = classify(r["raw_class"])
    key = strategy_class
    a = agg.setdefault(key, {
        "strategy_class": strategy_class,
        "sources": set(),
        "completed": 0,
        "wins": 0,
        "losses": 0,
        "gross_pnl": 0.0,
        "fee_drag": 0.0,
        "net_pnl": 0.0,
        "profit_gross": 0.0,
        "loss_gross": 0.0,
    })
    completed = int(r["completed"] or 0)
    wins = int(r["wins"] or 0)
    losses = int(r["losses"] or 0)
    gross = float(r["gross_pnl"] or 0)
    fee = float(r["fee_drag_estimate"] or 0)
    net = float(r["net_pnl_estimate"] or 0)

    a["sources"].add(r["source_table"])
    a["completed"] += completed
    a["wins"] += wins
    a["losses"] += losses
    a["gross_pnl"] += gross
    a["fee_drag"] += fee
    a["net_pnl"] += net

    if gross >= 0:
        a["profit_gross"] += gross
    else:
        a["loss_gross"] += abs(gross)

ranked = []
for a in agg.values():
    completed = a["completed"]
    pf = a["profit_gross"] / a["loss_gross"] if a["loss_gross"] > 0 else None
    expectancy = a["gross_pnl"] / completed if completed else 0.0
    avg_net = a["net_pnl"] / completed if completed else 0.0
    winrate = a["wins"] / completed if completed else 0.0

    if completed >= 50 and pf is not None and pf >= 1.5 and expectancy > 0 and avg_net > 0:
        verdict = "PROMOTE_TO_RESEARCH_CANDIDATE"
    elif completed >= 30 and expectancy > 0:
        verdict = "WATCH"
    elif completed < 30:
        verdict = "INSUFFICIENT_DATA"
    else:
        verdict = "REJECT"

    ranked.append({
        **a,
        "profit_factor": pf or 0.0,
        "expectancy": expectancy,
        "avg_net": avg_net,
        "winrate": winrate,
        "verdict": verdict,
    })

ranked.sort(key=lambda x: (x["verdict"] != "PROMOTE_TO_RESEARCH_CANDIDATE", -x["profit_factor"], -x["completed"]))

print("\nCLASS_RANKING")
for r in ranked:
    print(
        "CLASS_ROW "
        f"strategy_class={r['strategy_class']} "
        f"sources={','.join(sorted(r['sources']))} "
        f"completed={r['completed']} "
        f"wins={r['wins']} "
        f"losses={r['losses']} "
        f"winrate={r['winrate']:.4f} "
        f"profit_factor={r['profit_factor']:.4f} "
        f"expectancy={r['expectancy']:.6f} "
        f"gross_pnl={r['gross_pnl']:.6f} "
        f"fee_drag_estimate={r['fee_drag']:.6f} "
        f"net_pnl_estimate={r['net_pnl']:.6f} "
        f"avg_net_per_trade={r['avg_net']:.6f} "
        f"verdict={r['verdict']}"
    )

best = ranked[0]["strategy_class"] if ranked else "NONE"
worst = ranked[-1]["strategy_class"] if ranked else "NONE"

print("\nDISCOVERY_SUMMARY")
print(f"classes_total={len(ranked)}")
print(f"best_class={best}")
print(f"worst_class={worst}")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("VERDICT=STRATEGY_CLASS_DISCOVERY_AUDIT_READY")
