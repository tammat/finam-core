#!/usr/bin/env python3
import os
import psycopg
from psycopg.rows import dict_row

dsn = os.environ["DATABASE_URL"]

def classify(strategy: str, payload_text: str) -> str:
    v = f"{strategy or ''} {payload_text or ''}".upper()
    if "MEAN_REVERSION" in v or "REVERSION" in v:
        return "MEAN_REVERSION"
    if "PULLBACK" in v or "RETEST" in v:
        return "PULLBACK"
    if "VOLATILITY" in v and "BREAKOUT" in v:
        return "VOLATILITY_BREAKOUT"
    if "BREAKOUT" in v:
        return "BREAKOUT"
    if "MOMENTUM" in v or "IMPULSE" in v:
        return "MOMENTUM"
    if "TREND" in v:
        return "TREND_FOLLOWING"
    if "COMPRESSION" in v or "EXPANSION" in v:
        return "COMPRESSION_EXPANSION"
    if "REGIME" in v:
        return "REGIME_SWITCH"
    return "UNKNOWN"

print("=== STRATEGY_CLASS_DISCOVERY_AUDIT_V2 ===")
print("mode=read_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("source_table=analytics_rs_bottom_runtime_dry_run_v1")

sql = """
select
    strategy,
    payload::text as payload_text,
    status,
    return_pct
from analytics_rs_bottom_runtime_dry_run_v1
where status in ('SUCCESS','FAILURE')
  and return_pct is not null
"""

with psycopg.connect(dsn, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

agg = {}

for r in rows:
    cls = classify(r.get("strategy"), r.get("payload_text"))
    a = agg.setdefault(cls, {
        "completed": 0,
        "wins": 0,
        "losses": 0,
        "gross_pnl": 0.0,
        "profit_sum": 0.0,
        "loss_sum": 0.0,
        "strategies": set(),
    })

    ret = float(r["return_pct"] or 0)
    a["completed"] += 1
    a["gross_pnl"] += ret
    a["strategies"].add(str(r.get("strategy") or "UNKNOWN"))

    if ret > 0:
        a["wins"] += 1
        a["profit_sum"] += ret
    else:
        a["losses"] += 1
        a["loss_sum"] += abs(ret)

print("\nCLASS_RANKING")

ranked = []
for cls, a in agg.items():
    completed = a["completed"]
    pf = a["profit_sum"] / a["loss_sum"] if a["loss_sum"] > 0 else 0.0
    expectancy = a["gross_pnl"] / completed if completed else 0.0
    fee_drag = completed * 0.02
    net_pnl = a["gross_pnl"] - fee_drag
    avg_net = net_pnl / completed if completed else 0.0
    winrate = a["wins"] / completed if completed else 0.0

    if completed >= 30 and pf >= 1.5 and expectancy > 0 and avg_net > 0:
        verdict = "PROMOTE_TO_RESEARCH_CANDIDATE"
    elif completed >= 15 and pf >= 1.0 and expectancy > 0:
        verdict = "WATCH"
    elif completed < 15:
        verdict = "INSUFFICIENT_DATA"
    else:
        verdict = "REJECT"

    ranked.append((cls, a, pf, expectancy, fee_drag, net_pnl, avg_net, winrate, verdict))

ranked.sort(key=lambda x: (x[8] != "PROMOTE_TO_RESEARCH_CANDIDATE", x[8] != "WATCH", -x[2], -x[1]["completed"]))

for cls, a, pf, expectancy, fee_drag, net_pnl, avg_net, winrate, verdict in ranked:
    print(
        "CLASS_ROW "
        f"strategy_class={cls} "
        f"strategies={','.join(sorted(a['strategies']))} "
        f"completed={a['completed']} "
        f"wins={a['wins']} "
        f"losses={a['losses']} "
        f"winrate={winrate:.4f} "
        f"profit_factor={pf:.4f} "
        f"expectancy={expectancy:.6f} "
        f"gross_pnl={a['gross_pnl']:.6f} "
        f"fee_drag_estimate={fee_drag:.6f} "
        f"net_pnl_estimate={net_pnl:.6f} "
        f"avg_net_per_trade={avg_net:.6f} "
        f"verdict={verdict}"
    )

best = ranked[0][0] if ranked else "NONE"
worst = ranked[-1][0] if ranked else "NONE"

print("\nDISCOVERY_SUMMARY")
print(f"classes_total={len(ranked)}")
print(f"best_class={best}")
print(f"worst_class={worst}")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("VERDICT=STRATEGY_CLASS_DISCOVERY_AUDIT_V2_READY")
