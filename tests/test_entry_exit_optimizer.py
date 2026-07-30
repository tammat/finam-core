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


def test_small_sample_never_promotes():
    assert not evaluate_walk_forward([{"actual_r": 0, "shadow_r": 1}] * 79)["status"].startswith("READY")


def test_forty_pairs_are_early_evidence_only():
    result = evaluate_walk_forward([{"actual_r": -0.1, "shadow_r": 0.2}] * 40)
    assert result["status"] == "SHADOW_EARLY_EVIDENCE"
    assert result["adaptive_gate"]["min_pairs"] == 80


def test_sparse_diverse_history_uses_sixty_fifteen_gate():
    from datetime import date, timedelta
    start = date(2026, 1, 1)
    rows = [{"actual_r": -0.1, "shadow_r": 0.2,
             "trade_date": (start + timedelta(days=index % 40)).isoformat(),
             "regime": ("range", "trend_up", "trend_down")[index % 3]}
            for index in range(60)]
    gate = adaptive_shadow_gate(rows)
    assert gate["gate"] == "SPARSE_60_15"
    result = evaluate_walk_forward(rows)
    assert result["status"] == "READY_FOR_PAPER_CONFIRMATION"
    assert result["oos_pairs"] == 15


def test_standard_gate_requires_time_and_regime_diversity():
    rows = [{"actual_r": -0.1, "shadow_r": 0.2,
             "trade_date": f"2026-01-{index % 10 + 1:02d}",
             "regime": "range" if index % 2 else "trend_up"}
            for index in range(80)]
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
