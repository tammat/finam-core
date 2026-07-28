from finam_core.strategy.regime_strategy_policy_v1 import resolve_regime_strategy_v1


def test_range_routes_to_mean_reversion():
    decision = resolve_regime_strategy_v1(trend="range", data_ready=True, stale=False)
    assert decision is not None
    assert decision.strategy_code == "MEAN_REVERSION_EQUITY"
    assert decision.allowed_side == "BOTH"


def test_uptrend_allows_only_long_breakout():
    decision = resolve_regime_strategy_v1(trend="trend_up", data_ready=True, stale=False)
    assert decision is not None
    assert decision.strategy_code == "VOLATILITY_BREAKOUT_EQUITY"
    assert decision.allows("BUY")
    assert not decision.allows("SELL")


def test_downtrend_allows_only_short_breakout():
    decision = resolve_regime_strategy_v1(trend="trend_down", data_ready=True, stale=False)
    assert decision is not None
    assert decision.allows("SELL")
    assert not decision.allows("BUY")


def test_unknown_or_unconfirmed_regime_is_fail_closed():
    assert resolve_regime_strategy_v1(
        trend="unknown", data_ready=True, stale=False
    ) is None
    assert resolve_regime_strategy_v1(
        trend="trend_up", data_ready=False, stale=False
    ) is None
    assert resolve_regime_strategy_v1(
        trend="trend_up", data_ready=True, stale=True
    ) is None
