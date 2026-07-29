from finam_core.analytics.entry_exit_optimizer import Bar, Variant, default_variants, evaluate_walk_forward, simulate_variant


def test_same_bar_stop_take_is_conservative():
    variant = Variant("v", "IMMEDIATE", 1.0, 2.0)
    out = simulate_variant(signal_price=100, side="LONG", atr=1, bars=[Bar(103, 98, 101)], variant=variant)
    assert out.reason == "TRAIL_OR_STOP"
    assert out.net_r == -1


def test_confirmation_can_filter_signal():
    variant = Variant("v", "CONFIRM_1", 1.0, 2.0)
    out = simulate_variant(signal_price=100, side="LONG", atr=1, bars=[Bar(100, 98, 99)], variant=variant)
    assert not out.entered and out.reason == "ENTRY_FILTERED"


def test_short_trailing_is_direction_aware():
    variant = Variant("v", "IMMEDIATE", 1.0, 3.0, 1.0, 0.5)
    out = simulate_variant(signal_price=100, side="SHORT", atr=1, bars=[Bar(100, 98, 98.5), Bar(99, 98, 98.7)], variant=variant)
    assert out.entered and out.net_r > 0


def test_small_sample_never_promotes():
    assert evaluate_walk_forward([{"actual_r": 0, "shadow_r": 1}] * 79)["status"] == "SHADOW_ACCUMULATION"


def test_search_space_is_bounded():
    assert len(default_variants("MEAN_REVERSION_EQUITY")) == 9
    assert len(default_variants("BR_CONSERVATIVE_BREAKOUT")) == 9
