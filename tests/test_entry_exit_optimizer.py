from finam_core.analytics.entry_exit_optimizer import (
    Bar, Variant, adaptive_shadow_gate, default_variants, evaluate_active_paper_champion,
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


def test_confirmation_candle_cannot_exit_before_close_entry():
    variant = Variant("v", "CONFIRM_1", 1.0, 2.0)
    bars = [Bar(103, 98, 101), Bar(102, 100.5, 101.5)]
    out = simulate_variant(signal_price=100, side="LONG", atr=1, bars=bars, variant=variant)
    assert out.entered and out.reason == "HORIZON_MARK"
    assert out.entry_price == 101


def test_retest_enters_at_confirmation_close_and_exits_from_next_bar():
    variant = Variant("v", "RETEST_3", 1.0, 2.0)
    bars = [Bar(101, 99, 100.5), Bar(101.5, 100.4, 101.0)]
    out = simulate_variant(signal_price=100, side="LONG", atr=1, bars=bars, variant=variant)
    assert out.entered and out.entry_price == 100.5
    assert out.reason == "HORIZON_MARK"


def test_trailing_uses_only_previous_completed_candle():
    variant = Variant("v", "IMMEDIATE", 2.0, 5.0, 0.5, 0.5)
    bars = [Bar(102, 99.5, 101.5), Bar(103, 100.75, 102.5)]
    out = simulate_variant(signal_price=100, side="LONG", atr=1, bars=bars, variant=variant)
    # First candle arms a 101.5 trail for the next candle.  The second candle
    # must exit there; it cannot first use its high=103 to invent stop=102.5.
    assert out.exit_price == 101.5
    assert out.net_r == 0.75


def test_roundtrip_cost_is_deducted_from_shadow_r():
    variant = Variant("v", "IMMEDIATE", 1.0, 2.0)
    out = simulate_variant(signal_price=100, side="LONG", atr=1,
                           bars=[Bar(102, 100, 102)], variant=variant,
                           roundtrip_cost_price=0.25)
    assert out.net_r == 1.75


def test_small_sample_never_promotes():
    assert not evaluate_walk_forward([{"actual_r": 0, "shadow_r": 1}] * 79)["status"].startswith("READY")


def test_forty_pairs_are_early_evidence_only():
    result = evaluate_walk_forward([{"actual_r": -0.1, "shadow_r": 0.2}] * 40)
    assert result["status"] == "SHADOW_EARLY_EVIDENCE"
    assert result["adaptive_gate"]["min_pairs"] == 60


def test_oos_reserve_accumulates_before_full_gate():
    result = evaluate_walk_forward([{"actual_r": -0.1, "shadow_r": 0.2}] * 9)
    assert result["oos_pairs"] == 2
    assert result["oos_provisional"] is True
    assert result["status"] == "SHADOW_ACCUMULATION"


def test_diverse_long_history_can_enter_challenger_at_forty_ten():
    from datetime import date, timedelta
    start = date(2026, 1, 1)
    rows = [{"actual_r": -0.1, "shadow_r": 0.2,
             "trade_date": (start + timedelta(days=index % 40)).isoformat(),
             "regime": ("range", "trend_up", "trend_down")[index % 3]}
            for index in range(40)]
    gate = adaptive_shadow_gate(rows)
    assert gate["gate"] == "DIVERSE_40_10_CHALLENGER"
    result = evaluate_walk_forward(rows)
    assert result["status"] == "READY_FOR_PAPER_CONFIRMATION"
    assert result["oos_pairs"] == 10


def test_standard_gate_requires_time_and_regime_diversity():
    rows = [{"actual_r": -0.1, "shadow_r": 0.2,
             "trade_date": f"2026-01-{index % 5 + 1:02d}",
             "regime": "range" if index % 2 else "trend_up"}
            for index in range(60)]
    assert adaptive_shadow_gate(rows)["gate"] == "INTRADAY_60_15"
    assert evaluate_walk_forward(rows)["status"] == "READY_FOR_PAPER_CONFIRMATION"


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
