from finam_core.analytics.entry_exit_optimizer import (
    Bar, EntryContext, Variant, adaptive_entry_decision, adaptive_entry_mode, adaptive_shadow_gate, default_variants, evaluate_active_paper_champion,
    evaluate_paper_challenger, evaluate_walk_forward, negative_control_check,
    parameter_plateau_check, simulate_variant,
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


def test_long_stop_gap_fills_at_open_plus_adverse_slippage():
    variant = Variant("v", "IMMEDIATE", 1.0, 3.0)
    out = simulate_variant(signal_price=100, side="LONG", atr=1,
                           bars=[Bar(99, 97, 98.5, 98)], variant=variant,
                           tick_size=0.5, stop_slippage_ticks=1)
    assert out.reason == "GAP_STOP"
    assert out.exit_price == 97.5
    assert out.net_r == -2.5


def test_short_stop_is_rounded_and_slipped_against_position():
    variant = Variant("v", "IMMEDIATE", 1.0, 3.0)
    out = simulate_variant(signal_price=100, side="SHORT", atr=1,
                           bars=[Bar(102, 100, 101.5, 101.2)], variant=variant,
                           tick_size=0.5, stop_slippage_ticks=1)
    assert out.exit_price == 102.0
    assert out.net_r == -2.0


def test_small_sample_never_promotes():
    assert not evaluate_walk_forward([{"actual_r": 0, "shadow_r": 1}] * 79)["status"].startswith("READY")


def test_forty_pairs_are_early_evidence_only():
    result = evaluate_walk_forward([{"actual_r": -0.1, "shadow_r": 0.2}] * 40)
    assert result["status"] == "SHADOW_EARLY_EVIDENCE"
    assert result["adaptive_gate"]["min_pairs"] == 60


def test_oos_reserve_accumulates_before_full_gate():
    result = evaluate_walk_forward(
        [{"actual_r": -0.1, "shadow_r": 0.2, "placebo_r": -0.1}] * 9)
    assert result["oos_pairs"] == 2
    assert result["oos_provisional"] is True
    assert result["status"] == "SHADOW_ACCUMULATION"
    assert result["negative_control"]["provisional"] is True
    assert result["negative_control"]["passed"] is True


def test_diverse_long_history_can_enter_challenger_at_forty_ten():
    from datetime import date, timedelta
    start = date(2026, 1, 1)
    rows = [{"actual_r": -0.1, "shadow_r": 0.2, "placebo_r": -0.1,
             "trade_date": (start + timedelta(days=index % 40)).isoformat(),
             "regime": ("range", "trend_up", "trend_down")[index % 3]}
            for index in range(40)]
    gate = adaptive_shadow_gate(rows)
    assert gate["gate"] == "DIVERSE_40_10_CHALLENGER"
    result = evaluate_walk_forward(rows)
    assert result["status"] == "READY_FOR_PAPER_CONFIRMATION"
    assert result["oos_pairs"] == 10


def test_standard_gate_requires_time_and_regime_diversity():
    rows = [{"actual_r": -0.1, "shadow_r": 0.2, "placebo_r": -0.1,
             "trade_date": f"2026-01-{index % 5 + 1:02d}",
             "regime": "range" if index % 2 else "trend_up"}
            for index in range(60)]
    assert adaptive_shadow_gate(rows)["gate"] == "INTRADAY_60_15"
    assert evaluate_walk_forward(rows)["status"] == "READY_FOR_PAPER_CONFIRMATION"


def test_explicit_purged_oos_must_meet_its_own_minimum():
    rows = [{"actual_r": -0.1, "shadow_r": 0.2,
             "trade_date": f"2026-01-{index % 10 + 1:02d}",
             "regime": ("range", "trend_up")[index % 2]}
            for index in range(60)]
    result = evaluate_walk_forward(rows, oos_rows=rows[-5:])
    assert result["status"] == "SHADOW_ACCUMULATION"
    assert result["oos_pairs"] == 5
    assert "purged OOS" in result["reason"]


def test_early_explicit_oos_reports_fact_not_synthetic_reserve():
    rows = [{"actual_r": -0.1, "shadow_r": 0.2, "placebo_r": -0.1}] * 39
    result = evaluate_walk_forward(rows, oos_rows=[])
    assert result["status"] == "SHADOW_ACCUMULATION"
    assert result["oos_pairs"] == 0


def test_negative_control_requires_candidate_to_beat_unconditional_entry():
    rows = ([{"shadow_r": 0.4, "placebo_r": -0.2}] * 20)
    result = negative_control_check(rows)
    assert result["passed"]
    assert result["delta_expectancy_r"] > 0


def test_negative_control_fails_closed_when_missing():
    result = negative_control_check([{"shadow_r": 0.4, "placebo_r": None}])
    assert not result["passed"]
    assert result["reason"] == "NO_PAIRED_PLACEBO_CONTROL"


def test_parameter_plateau_rejects_isolated_peak():
    metrics = {
        "IMMEDIATE_S1.2_R1.1": {"shadow_oos_r": 0.1, "stop_atr": 1.2},
        "IMMEDIATE_S1.5_R1.4": {"shadow_oos_r": 0.8, "stop_atr": 1.5},
        "IMMEDIATE_S1.8_R1.8": {"shadow_oos_r": 0.05, "stop_atr": 1.8},
    }
    result = parameter_plateau_check("IMMEDIATE_S1.5_R1.4", metrics)
    assert not result["passed"]
    assert result["reason"] == "ISOLATED_PARAMETER_PEAK"


def test_parameter_plateau_accepts_adjacent_stable_region():
    metrics = {
        "IMMEDIATE_S1.2_R1.1": {"shadow_oos_r": 0.31, "stop_atr": 1.2},
        "IMMEDIATE_S1.5_R1.4": {"shadow_oos_r": 0.4, "stop_atr": 1.5},
        "IMMEDIATE_S1.8_R1.8": {"shadow_oos_r": 0.28, "stop_atr": 1.8},
    }
    result = parameter_plateau_check("IMMEDIATE_S1.5_R1.4", metrics)
    assert result["passed"]
    assert len(result["supporting_neighbors"]) == 2


def test_search_space_is_bounded():
    assert len(default_variants("MEAN_REVERSION_EQUITY")) == 12
    assert len(default_variants("BR_CONSERVATIVE_BREAKOUT")) == 12


def test_adaptive_entry_routes_strong_trend_to_immediate():
    context = EntryContext(atr_percentile=0.55, relative_volume=1.4,
                           regime="trend_up", cost_to_atr=0.03,
                           strategy="BR_CONSERVATIVE_BREAKOUT")
    assert adaptive_entry_mode(context, take_atr=2.4) == "IMMEDIATE"


def test_adaptive_entry_waits_for_confirmation_in_extreme_volatility():
    context = EntryContext(atr_percentile=0.9, relative_volume=1.4,
                           regime="trend_up", cost_to_atr=0.03)
    assert adaptive_entry_mode(context, take_atr=2.4) == "CONFIRM_1"


def test_adaptive_entry_skips_weak_liquidity_or_expensive_signal():
    weak = EntryContext(relative_volume=0.5)
    expensive = EntryContext(relative_volume=1.0, cost_to_atr=0.5)
    assert adaptive_entry_mode(weak, take_atr=2.0) == "SKIP"
    assert adaptive_entry_mode(expensive, take_atr=2.0) == "SKIP"
    assert adaptive_entry_decision(weak, take_atr=2.0) == ("SKIP", "LOW_RELATIVE_VOLUME")


def test_adaptive_range_mean_reversion_uses_retest():
    context = EntryContext(relative_volume=1.0, regime="range_low_vol",
                           strategy="MEAN_REVERSION_EQUITY")
    assert adaptive_entry_mode(context, take_atr=1.3) == "RETEST_3"


def test_adaptive_retest_uses_atr_zone_without_future_bar_leakage():
    variant = Variant("v", "ADAPTIVE", 1.2, 1.3)
    context = EntryContext(atr_percentile=0.5, relative_volume=1.0,
                           regime="range_low_vol", strategy="MEAN_REVERSION_EQUITY")
    bars = [Bar(high=100.4, low=100.15, close=100.25),
            Bar(high=100.6, low=100.2, close=100.5)]
    out = simulate_variant(signal_price=100, side="LONG", atr=1,
                           bars=bars, variant=variant, entry_context=context)
    assert out.entered and out.entry_price == 100.25


def test_adaptive_retest_rejects_unknown_runaway_then_retest_order():
    variant = Variant("v", "ADAPTIVE", 1.2, 1.3)
    context = EntryContext(atr_percentile=0.5, relative_volume=1.0,
                           regime="range_low_vol", strategy="MEAN_REVERSION_EQUITY")
    out = simulate_variant(signal_price=100, side="LONG", atr=1,
                           bars=[Bar(high=100.8, low=100.1, close=100.3)],
                           variant=variant, entry_context=context)
    assert not out.entered
    assert out.entry_decision == "RETEST_3"
    assert out.entry_decision_reason.endswith("RUNAWAY_OR_AMBIGUOUS_BAR")


def test_entry_context_query_requires_completed_bar_cutoff():
    source = open(
        "src/scripts/analytics/build_entry_exit_optimizer_v1.py", encoding="utf-8"
    ).read()
    assert 'completed_cutoff = trade["entry_ts"] - timeframe_delta(timeframe)' in source
    assert "ts <= %s" in source


def test_optimizer_uses_complete_v5_signal_funnel_and_purged_split():
    source = open(
        "src/scripts/analytics/build_entry_exit_optimizer_v1.py", encoding="utf-8"
    ).read()
    assert "FROM signals s" in source
    assert "s.status IN ('FILLED','RISK_REJECTED')" in source
    assert "entry_exit_signal_shadow_pair_v2" in source
    assert "purged_temporal_split(" in source
    assert "embargo=horizon" in source
    assert "placebo_net_r" in source
    assert "entry_exit_family_evidence_v1" in source
    assert "parameter_plateau_check" in source


def test_paper_challenger_requires_fresh_forward_sample():
    result = evaluate_paper_challenger([{"actual_r": 0.0, "shadow_r": 0.5}] * 29)
    assert result["status"] == "PAPER_CHALLENGER"
    assert result["pairs"] == 29


def test_paper_challenger_can_become_champion_ready():
    rows = [{"actual_r": -0.1, "shadow_r": 0.3,
             "regime": "range" if index < 15 else "trend"}
            for index in range(30)]
    result = evaluate_paper_challenger(rows)
    assert result["status"] == "READY_FOR_CHAMPION_CONFIRMATION"
    assert result["expectancy_delta_r"] > 0


def test_challenger_rejects_edge_without_regime_support():
    rows = [{"actual_r": -0.1, "shadow_r": 0.3, "regime": "UNKNOWN"}] * 30
    result = evaluate_paper_challenger(rows)
    assert result["status"] == "KEEP_PAPER_CHALLENGER"
    assert not result["checks"]["minimum_per_regime"]


def test_challenger_penalizes_filtered_signal_coverage():
    rows = ([{"actual_r": -0.1, "shadow_r": 0.3, "regime": "range"}] * 30
            + [{"actual_r": 0.1, "shadow_r": None, "regime": "range"}] * 40)
    result = evaluate_paper_challenger(rows)
    assert not result["checks"]["candidate_signal_coverage"]


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
