from __future__ import annotations

from scripts import build_strategy_execution_runner_v1 as runner


bars = [runner.Bar(ts=i, close=100.0 + (i * 0.05)) for i in range(240)]


def run_with_threshold(threshold: float):
    return runner.build_trades(
        {
            "strategy_code": "MOMENTUM_CONTINUATION_V1",
            "parameter_json": {
                "lookback": 20,
                "hold": 5,
                "threshold": threshold,
                "commission": 0.0,
                "slippage": 0.0,
            },
        },
        bars,
    )


low_threshold_trades = run_with_threshold(0.5)
high_threshold_trades = run_with_threshold(2.5)

assert len(low_threshold_trades) > 0
assert len(high_threshold_trades) == 0

print(f"low_threshold_trades={len(low_threshold_trades)}")
print(f"high_threshold_trades={len(high_threshold_trades)}")
print("threshold_unit=PERCENT")
print("VERDICT=TEST_STRATEGY_EXECUTION_MOMENTUM_THRESHOLD_V1_OK")
