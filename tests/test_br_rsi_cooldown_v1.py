from datetime import datetime, timezone

from finam_core.strategy.br_conservative_breakout import BrConservativeBreakout


def test_regime_rsi_is_computed_from_closed_regime_bars():
    strategy = BrConservativeBreakout()
    for price in range(100, 115):
        strategy.on_regime_bar(datetime.now(timezone.utc), price, price + 1, price - 1, price)
    assert strategy.regime_rsi is not None
    assert strategy.regime_rsi_state == "READY"
    assert strategy._rsi_filter_allows("BUY")
    assert not strategy._rsi_filter_allows("SELL")


def test_signal_cooldown_expires_by_bar_count():
    strategy = BrConservativeBreakout(signal_cooldown_bars=3, enable_rsi_filter=False)
    strategy._register_signal("BUY")
    assert strategy._signal_blocked_by_cooldown("BUY")
    for _ in range(3):
        strategy.on_signal_bar(datetime.now(timezone.utc), 100, 101, 99, 100)
    assert not strategy._signal_blocked_by_cooldown("BUY")
