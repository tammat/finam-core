#!/usr/bin/env python3
from datetime import datetime, timezone, timedelta

print("=== EXIT_POLICY_ENGINE_SCAFFOLD_V1 ===")
print("mode=scaffold_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

from finam_core.research.exit_policy.policy_base import ClosedTradeInput
from finam_core.research.exit_policy.policy_registry import PolicyRegistry
from finam_core.research.exit_policy.policies.time_stop_5m import TimeStop5mPolicy
from finam_core.research.exit_policy.replay_engine import ReplayEngine
from finam_core.research.exit_policy.evaluator import PolicyEvaluator
from finam_core.research.exit_policy.scorecard import PolicyScorecard

registry = PolicyRegistry()
registry.register(TimeStop5mPolicy())

now = datetime.now(timezone.utc)
trades = [
    ClosedTradeInput(
        trade_id="scaffold-1",
        symbol="TEST@RTSX",
        entry_ts=now,
        exit_ts=now + timedelta(minutes=10),
        entry_price=100.0,
        exit_price=101.0,
        net_pnl=1.0,
        commission=0.01,
    ),
    ClosedTradeInput(
        trade_id="scaffold-2",
        symbol="TEST@RTSX",
        entry_ts=now,
        exit_ts=now + timedelta(minutes=20),
        entry_price=100.0,
        exit_price=99.5,
        net_pnl=-0.5,
        commission=0.01,
    ),
]

engine = ReplayEngine(registry)
results = engine.replay(trades)

metrics = PolicyEvaluator().evaluate(results)
lines = PolicyScorecard().render_lines(metrics)

print("\nREGISTERED_POLICIES")
for name in registry.names():
    print(f"POLICY name={name}")

print("\nSCORECARD")
for line in lines:
    print(line)

print("\nVERDICT=EXIT_POLICY_ENGINE_SCAFFOLD_READY")
