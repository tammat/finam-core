from finam_core.backtest.engine import BacktestEngine
from finam_core.backtest.simple_trend import SimpleTrendStrategy
from finam_core.backtest.data_loader import load_csv
from finam_core.risk.risk_engine import RiskEngine
from finam_core.analytics.trade_stats import TradeStats

stats = TradeStats(equity)

print("Sharpe:", stats.sharpe())
print("Max DD:", stats.max_drawdown())
bars = load_csv("ngh6_5m.csv")

engine = BacktestEngine(
    strategy=SimpleTrendStrategy(),
    risk_engine=RiskEngine()
)

equity = engine.run(bars)

print("Final equity:", equity[-1])