from datetime import datetime,timedelta,timezone
from pathlib import Path

from scripts.build_strategy_execution_runner_v1 import Bar,build_trades


def _bars(values):
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    return [Bar(start+timedelta(minutes=5*i),value,100+i) for i,value in enumerate(values)]


def test_three_orthogonal_algorithms_are_database_configured() -> None:
    migration=Path("sql/analytics/075_orthogonal_edge_search_algorithms_v1.sql").read_text()
    for code in ("EMA_TREND_FILTER_V1","VOLATILITY_SCALED_MOMENTUM_V1","DONCHIAN_VOLATILITY_BREAKOUT_V1"):
        assert code in migration
    assert "gate_policy" in migration
    assert "contract_aware" in migration


def test_ema_trend_filter_detects_persistent_trend() -> None:
    values=[100+i*0.15 for i in range(180)]
    trades=build_trades({"strategy_code":"EMA_TREND_FILTER_V1","parameter_json":{"fast":10,"slow":40,"lookback":40,"hold":9,"threshold":0.15}},_bars(values))
    assert trades and all(trade.side=="BUY" for trade in trades)


def test_volatility_scaled_momentum_and_buffered_donchian_are_independent() -> None:
    values=[100+i*0.02+((i%5)-2)*0.01 for i in range(100)]+[103+i*0.20 for i in range(80)]
    bars=_bars(values)
    momentum=build_trades({"strategy_code":"VOLATILITY_SCALED_MOMENTUM_V1","parameter_json":{"lookback":40,"vol_lookback":20,"hold":5,"threshold":0.5}},bars)
    donchian=build_trades({"strategy_code":"DONCHIAN_VOLATILITY_BREAKOUT_V1","parameter_json":{"lookback":40,"hold":9,"threshold":0.25}},bars)
    assert momentum and donchian
    assert "_orthogonal_side" in Path("src/scripts/build_strategy_execution_runner_v1.py").read_text()
