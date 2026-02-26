import os
import time

os.environ["RISK_LATENCY"] = "1"

from risk.pre_trade_risk import PreTradeRiskEngine, RiskConfig
from accounting.position_manager import PositionManager

N = 50_000

engine = PreTradeRiskEngine(
    RiskConfig(
        max_risk_per_trade=1_000_000,
        max_total_exposure=10_000_000,
        daily_loss_limit=1_000_000,
        max_portfolio_heat=10.0,
    )
)

pm = PositionManager(starting_cash=1_000_000)
ctx = pm.get_context()

start = time.perf_counter()

for _ in range(N):
    engine.validate(ctx, "SI", "BUY", 1, 100)

end = time.perf_counter()

elapsed = end - start

print("Total calls:", N)
print("Total time:", round(elapsed, 4), "sec")
print("Throughput:", round(N / elapsed), "calls/sec")
print("Latency snapshot:", engine.latency.snapshot())