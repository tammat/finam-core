from finam_core.strategy.equities.volatility_breakout_equity import (
    VolatilityBreakoutConfig,
    VolatilityBreakoutEquity,
)


def _warm(strategy, prices):
    for price in prices:
        assert strategy.on_quote("X5@MISX", price, high=price, volume=100, atr=2, regime="range_high_vol") is None


def test_upward_breakout_creates_buy():
    strategy = VolatilityBreakoutEquity(VolatilityBreakoutConfig(lookback=3, min_atr_pct=0, volume_mult=0))
    _warm(strategy, [100, 101, 102])
    signal = strategy.on_quote("X5@MISX", 104, high=104, volume=100, atr=2, regime="trend_up_high_vol")
    assert signal is not None
    assert signal.side == "BUY"
    assert signal.reason == "range_breakout_up_with_volume"


def test_downward_breakout_creates_sell():
    strategy = VolatilityBreakoutEquity(VolatilityBreakoutConfig(lookback=3, min_atr_pct=0, volume_mult=0))
    _warm(strategy, [102, 101, 100])
    signal = strategy.on_quote("X5@MISX", 98, high=99, volume=100, atr=2, regime="trend_down_high_vol")
    assert signal is not None
    assert signal.side == "SELL"
    assert signal.stop_price > signal.entry_price
    assert signal.take_profit < signal.entry_price
    assert signal.reason == "range_breakout_down_with_volume"


def test_short_can_be_disabled():
    strategy = VolatilityBreakoutEquity(VolatilityBreakoutConfig(
        lookback=3, min_atr_pct=0, volume_mult=0, allow_short=False,
    ))
    _warm(strategy, [102, 101, 100])
    assert strategy.on_quote("X5@MISX", 98, high=99, volume=100, atr=2, regime="trend_down_high_vol") is None


def test_uptrend_blocks_short_breakout():
    strategy = VolatilityBreakoutEquity(
        VolatilityBreakoutConfig(lookback=3, min_atr_pct=0, volume_mult=0)
    )
    _warm(strategy, [102, 101, 100])
    assert strategy.on_quote(
        "X5@MISX", 98, high=99, volume=100, atr=2, regime="trend_up_high_vol"
    ) is None


def test_downtrend_blocks_long_breakout():
    strategy = VolatilityBreakoutEquity(
        VolatilityBreakoutConfig(lookback=3, min_atr_pct=0, volume_mult=0)
    )
    _warm(strategy, [100, 101, 102])
    assert strategy.on_quote(
        "X5@MISX", 104, high=104, volume=100, atr=2, regime="trend_down_high_vol"
    ) is None
