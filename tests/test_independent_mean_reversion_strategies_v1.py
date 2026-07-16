from scripts.build_strategy_execution_runner_v1 import Bar, build_trades


def test_rsi_bollinger_and_vwap_do_not_share_one_signal_formula():
    bars = []
    for index in range(140):
        close = 100.0 + ((index % 18) - 9) * 0.35 + (4.0 if index % 31 == 0 else 0.0)
        volume = 100.0 if index % 7 else 5000.0
        bars.append(Bar(index, close, volume))

    parameters = {"lookback": 20, "hold": 3, "threshold": 1.5}
    signatures = {}
    for code in ("VWAP_REVERSION_V2", "BOLLINGER_REVERSION_V1", "RSI_MEAN_REVERSION_V1"):
        strategy_parameters = dict(parameters)
        if code == "RSI_MEAN_REVERSION_V1":
            strategy_parameters["threshold"] = 45.0
        trades = build_trades({"strategy_code": code, "parameter_json": strategy_parameters}, bars)
        signatures[code] = [(trade.side, trade.entry_ts) for trade in trades]

    assert all(signatures.values())
    assert len({tuple(value) for value in signatures.values()}) == 3


def test_vwap_requires_real_volume_evidence():
    bars = [Bar(index, 100.0 + (index % 9), 0.0) for index in range(100)]
    trades = build_trades(
        {"strategy_code": "VWAP_REVERSION_V2", "parameter_json": {"lookback": 20, "hold": 3, "threshold": 1.0}},
        bars,
    )
    assert trades == []
