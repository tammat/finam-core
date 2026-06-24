#!/usr/bin/env python3
import os
import psycopg
from psycopg.rows import dict_row

from finam_core.research.exit_policy.policy_base import ClosedTradeInput
from finam_core.research.exit_policy.policy_registry import PolicyRegistry
from finam_core.research.exit_policy.policies.time_stop_5m import TimeStop5mPolicy
from finam_core.research.exit_policy.replay_engine import ReplayEngine
from finam_core.research.exit_policy.evaluator import PolicyEvaluator
from finam_core.research.exit_policy.scorecard import PolicyScorecard

dsn = os.environ["DATABASE_URL"]

print("=== TIME_STOP_5M_CLOSED_TRADES_REPLAY_V1 ===")
print("mode=read_only_replay")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("source_table=closed_trades")
print("policy=TIME_STOP_5M")
print("note=scaffold_policy_uses_real_exit_price_until_market_bar_replay_v1")

sql = """
select
    row_number() over (order by entry_ts, exit_ts)::text as trade_id,
    coalesce(trade_source, 'UNKNOWN') as symbol,
    entry_ts,
    exit_ts,
    entry_price,
    exit_price,
    net_pnl,
    coalesce(commission, 0) as commission
from closed_trades
where entry_ts is not null
  and exit_ts is not null
  and entry_price is not null
  and exit_price is not null
  and net_pnl is not null
order by entry_ts, exit_ts
"""

with psycopg.connect(dsn, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

trades: list[ClosedTradeInput] = []
for r in rows:
    trades.append(
        ClosedTradeInput(
            trade_id=str(r["trade_id"]),
            symbol=str(r["symbol"]),
            entry_ts=r["entry_ts"],
            exit_ts=r["exit_ts"],
            entry_price=float(r["entry_price"]),
            exit_price=float(r["exit_price"]),
            net_pnl=float(r["net_pnl"]),
            commission=float(r["commission"] or 0.0),
        )
    )

registry = PolicyRegistry()
registry.register(TimeStop5mPolicy())

results = ReplayEngine(registry).replay(trades)
metrics = PolicyEvaluator().evaluate(results)
lines = PolicyScorecard().render_lines(metrics)

print("\nREPLAY_INPUT")
print(f"closed_trades_loaded={len(trades)}")
print(f"virtual_results={len(results)}")

print("\nREGISTERED_POLICIES")
for name in registry.names():
    print(f"POLICY name={name}")

print("\nSCORECARD")
for line in lines:
    print(line)

print("\nLIMITATION")
print("TIME_STOP_5M currently clamps virtual_exit_ts but keeps real exit_price/net_pnl")
print("next_required=TIME_STOP_5M_MARKET_BAR_REPLAY_V1")

print("\nVERDICT=TIME_STOP_5M_CLOSED_TRADES_REPLAY_READY")
