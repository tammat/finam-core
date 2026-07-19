from finam_core.signals.signal_router import SignalRouter


def test_router_preserves_canonical_trade_identity_and_prices() -> None:
    routed = SignalRouter().route(
        {
            "signal_id": "smart-BRQ6-1",
            "symbol": "BRQ6@RTSX",
            "continuous_symbol": "BR_CONT",
            "side": "BUY",
            "qty": 1,
            "entry_price": 90.16,
            "stop_loss": 88.36,
            "take_profit": 93.76,
            "strategy": "BR_CONSERVATIVE_BREAKOUT",
            "timeframe": "M5",
            "horizon": "INTRADAY",
            "source": "smart_entry_retest",
            "reason": "smart_entry_retest_br_manual_candidate",
            "features": {"atr": 1.8, "strategy": "BR_CONSERVATIVE_BREAKOUT"},
        }
    )

    assert routed.allowed is True
    assert routed.intent.signal_id == "smart-BRQ6-1"
    assert routed.intent.strategy == "BR_CONSERVATIVE_BREAKOUT"
    assert routed.intent.entry_price == 90.16
    assert routed.intent.stop_price == 88.36
    assert routed.intent.take_profit == 93.76
    assert routed.intent.timeframe == "M5"
    assert routed.intent.horizon == "INTRADAY"
    assert routed.intent.continuous_symbol == "BR_CONT"


def test_router_restores_strategy_and_entry_from_features() -> None:
    routed = SignalRouter().route(
        {
            "symbol": "SBERP@MISX",
            "side": "BUY",
            "qty": 1,
            "price": 300.0,
            "strategy": "UNKNOWN_STRATEGY",
            "features": {
                "strategy": "VOLATILITY_BREAKOUT_EQUITY",
                "entry": 300.0,
                "stop": 294.0,
                "take": 312.0,
                "atr": 6.0,
            },
        }
    )

    assert routed.allowed is True
    assert routed.intent.strategy == "VOLATILITY_BREAKOUT_EQUITY"
    assert routed.intent.entry_price == 300.0
    assert routed.intent.stop_price == 294.0
    assert routed.intent.take_profit == 312.0
    assert "UNKNOWN_STRATEGY" not in routed.intent.signal_id
