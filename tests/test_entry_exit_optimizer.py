from finam_core.analytics.entry_exit_optimizer import (
    Bar, Variant, default_variants, evaluate_active_paper_champion,
    evaluate_paper_challenger, evaluate_walk_forward, simulate_variant,
)


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


def test_paper_challenger_requires_fresh_forward_sample():
    result = evaluate_paper_challenger([{"actual_r": 0.0, "shadow_r": 0.5}] * 29)
    assert result["status"] == "PAPER_CHALLENGER"
    assert result["pairs"] == 29


def test_paper_challenger_can_become_champion_ready():
    rows = [{"actual_r": -0.1, "shadow_r": 0.3}] * 30
    result = evaluate_paper_challenger(rows)
    assert result["status"] == "READY_FOR_CHAMPION_CONFIRMATION"
    assert result["expectancy_delta_r"] > 0


def test_active_champion_waits_for_twenty_trades_before_soft_guard():
    result = evaluate_active_paper_champion([{"actual_r": -0.1}] * 19, validated_drawdown_r=2)
    assert result["status"] == "MONITOR"


def test_active_champion_marks_negative_expectancy_degraded():
    rows = [{"actual_r": 0.1}] * 4 + [{"actual_r": -0.2}] * 16
    result = evaluate_active_paper_champion(rows, validated_drawdown_r=3)
    assert result["status"] == "DEGRADED"


def test_active_champion_drawdown_triggers_emergency_rollback():
    rows = [{"actual_r": -0.4}] * 10
    result = evaluate_active_paper_champion(rows, validated_drawdown_r=2)
    assert result["status"] == "ROLLBACK_NOW"
    assert result["hard_drawdown_limit_r"] == 3
