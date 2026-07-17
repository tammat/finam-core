from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.build_strategy_execution_runner_v1 import Bar, build_trades


ROOT = Path(__file__).resolve().parents[1]


def bars(own, reference):
    start = datetime(2026,1,1,tzinfo=timezone.utc)
    return [Bar(start+timedelta(minutes=5*i),float(value),100.0,float(reference[i]))
            for i,value in enumerate(own)]


def test_relative_strength_uses_reference_return() -> None:
    reference = [100.0] * 140
    own = [100.0 + i * 0.2 for i in range(140)]
    trades = build_trades({"strategy_code":"RELATIVE_STRENGTH_V1",
        "parameter_json":{"lookback":20,"hold":3,"threshold":0.25}},bars(own,reference))
    assert trades and all(trade.side == "BUY" for trade in trades)


def test_intermarket_spread_reversion_uses_synchronized_pair() -> None:
    reference = [100.0] * 180
    own = [100.0 + (8.0 if i % 30 == 0 else 0.05 * (i % 5)) for i in range(180)]
    trades = build_trades({"strategy_code":"INTERMARKET_SPREAD_REVERSION_V1",
        "parameter_json":{"lookback":20,"hold":3,"threshold":1.5}},bars(own,reference))
    assert trades
    assert any(trade.side == "SELL" for trade in trades)


def test_reference_strategy_refuses_missing_reference_data() -> None:
    series = [Bar(i,100.0+i*.1,100.0) for i in range(140)]
    trades = build_trades({"strategy_code":"RELATIVE_STRENGTH_V1",
        "parameter_json":{"lookback":20,"hold":3,"threshold":0.25}},series)
    assert trades == []


def test_registry_copies_strict_gates_and_scopes_reference_markets() -> None:
    sql = (ROOT / "sql/analytics/089_edge_search_relative_intermarket_v1.sql").read_text()
    assert "SELECT gate_policy" in sql and "DONCHIAN_VOL_BREAKOUT" in sql
    assert "reference_symbol" in sql and "target_symbols" in sql
    assert "V1_RELATIVE_INTERMARKET_STRICT_GATES" in sql
    assert "min_profit_factor" not in sql


def test_reference_series_is_used_by_regime_and_walkforward_paths() -> None:
    regime = (ROOT / "src/scripts/build_edge_regime_hypothesis_discovery_v2.py").read_text()
    walkforward = (ROOT / "src/scripts/build_walkforward_edge_search_v3.py").read_text()
    for source in (regime,walkforward):
        assert "_attach_reference" in source
        assert 'get("reference_symbol")' in source
        assert "strategy_bars" in source
