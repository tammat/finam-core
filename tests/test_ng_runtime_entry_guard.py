from finam_core.strategy.futures.ng_runtime_entry_guard import (
    evaluate_ng_directional_entry_guard, evaluate_ng_entry_guard,
)


def test_ng_is_blocked_when_universe_disables_all_contracts():
    result = evaluate_ng_entry_guard(symbol="NGQ6@RTSX", enabled_symbols=(), kill_switch_active=False, seconds_since_last=None)
    assert not result.allowed and result.reason == "NG_RUNTIME_UNIVERSE_DISABLED"


def test_only_canonical_enabled_contract_is_allowed():
    wrong = evaluate_ng_entry_guard(symbol="NGU6@RTSX", enabled_symbols=("NGQ6@RTSX",), kill_switch_active=False, seconds_since_last=None)
    right = evaluate_ng_entry_guard(symbol="NGQ6@RTSX", enabled_symbols=("NGQ6@RTSX",), kill_switch_active=False, seconds_since_last=None)
    assert not wrong.allowed and right.allowed


def test_kill_switch_prevents_signal_churn():
    result = evaluate_ng_entry_guard(symbol="NGQ6@RTSX", enabled_symbols=("NGQ6@RTSX",), kill_switch_active=True, seconds_since_last=None)
    assert result.reason == "KILL_SWITCH_ACTIVE_PRE_SIGNAL"


def test_cooldown_blocks_repeated_entry():
    result = evaluate_ng_entry_guard(symbol="NGQ6@RTSX", enabled_symbols=("NGQ6@RTSX",), kill_switch_active=False, seconds_since_last=20, cooldown_seconds=180)
    assert not result.allowed and result.reason == "NG_ENTRY_COOLDOWN"


def _direction(**overrides):
    values = dict(
        side="BUY", trend="range", normalized_slope=0.08,
        source_version="CANDLE_REGIME_V3", data_ready=True, stale=False,
        confirmed_bars=3, regime_bar_key="2026-07-29T19:00:00+00:00",
        consumed_fingerprints=set(), symbol="NGQ6@RTSX", slope_epsilon=0.02,
    )
    values.update(overrides)
    return evaluate_ng_directional_entry_guard(**values)


def test_ng_long_requires_positive_direction_even_in_range():
    assert _direction().allowed
    blocked = _direction(normalized_slope=-0.08)
    assert not blocked.allowed and blocked.reason == "NG_LONG_DIRECTION_NOT_CONFIRMED"


def test_ng_short_requires_negative_direction():
    assert _direction(side="SELL", normalized_slope=-0.08).allowed
    blocked = _direction(side="SELL", normalized_slope=0.08)
    assert not blocked.allowed and blocked.reason == "NG_SHORT_DIRECTION_NOT_CONFIRMED"


def test_ng_same_regime_bar_cannot_open_twice():
    fingerprint = "NGQ6@RTSX:BUY:2026-07-29T19:00:00+00:00"
    blocked = _direction(consumed_fingerprints={fingerprint})
    assert not blocked.allowed and blocked.reason == "NG_DUPLICATE_REGIME_BAR_FINGERPRINT"


def test_ng_directional_guard_fails_closed_on_stale_regime():
    blocked = _direction(stale=True)
    assert not blocked.allowed and blocked.reason == "NG_DIRECTIONAL_REGIME_NOT_READY"
