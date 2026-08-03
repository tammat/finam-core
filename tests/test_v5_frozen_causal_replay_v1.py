from scripts.run_v5_frozen_causal_replay_v1 import diagnostic_verdict


def test_reachability_failure_is_detected_before_profit_claim() -> None:
    assert diagnostic_verdict(
        source_signals=20, completed=0, entry_rate=0.0,
        expectancy_r=None, edge_r=None,
    ) == ("REACHABILITY_FAIL", "ENTRY_RATE_BELOW_5_PERCENT")


def test_small_sample_cannot_be_promoted() -> None:
    assert diagnostic_verdict(
        source_signals=6, completed=3, entry_rate=0.5,
        expectancy_r=1.0, edge_r=1.0,
    )[0] == "INSUFFICIENT_COMPLETED"


def test_positive_expectancy_must_beat_placebo() -> None:
    assert diagnostic_verdict(
        source_signals=10, completed=8, entry_rate=0.8,
        expectancy_r=0.2, edge_r=-0.1,
    )[0] == "NO_PLACEBO_EDGE"


def test_promising_is_diagnostic_only_after_all_checks() -> None:
    assert diagnostic_verdict(
        source_signals=10, completed=8, entry_rate=0.8,
        expectancy_r=0.2, edge_r=0.1,
    )[0] == "PROMISING_DIAGNOSTIC"
