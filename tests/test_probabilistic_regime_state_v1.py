from finam_core.regime.regime_state_v1 import regime_probabilities_v1, resolve_regime_state_v1


def test_probabilities_are_normalized_and_trend_dominates_strong_move() -> None:
    result = regime_probabilities_v1(
        mx_trend="UP", mx_strength=1.0, rvi_regime="LOW_VOL", rvi_percentile=0.1,
    )
    assert abs(sum(result.values()) - 1.0) < 1e-12
    assert result["TREND"] > result["RANGE"]
    assert result["TREND"] > result["SHOCK"]


def test_high_volatility_can_make_shock_dominant() -> None:
    result = regime_probabilities_v1(
        mx_trend="RANGE", mx_strength=0.0, rvi_regime="HIGH_VOL", rvi_percentile=1.0,
    )
    assert result["SHOCK"] == max(result.values())


def test_hysteresis_requires_three_confirmations() -> None:
    probabilities = {"TREND": 0.10, "RANGE": 0.20, "SHOCK": 0.70}
    first = resolve_regime_state_v1(
        probabilities=probabilities, previous_stable_family="TREND",
        previous_pending_family=None,
    )
    second = resolve_regime_state_v1(
        probabilities=probabilities, previous_stable_family=first.stable_family,
        previous_pending_family=first.pending_family, previous_pending_count=first.pending_count,
    )
    third = resolve_regime_state_v1(
        probabilities=probabilities, previous_stable_family=second.stable_family,
        previous_pending_family=second.pending_family, previous_pending_count=second.pending_count,
    )
    assert first.stable_family == second.stable_family == "TREND"
    assert third.stable_family == "SHOCK"
    assert third.switched is True


def test_low_confidence_candidate_does_not_start_switch() -> None:
    state = resolve_regime_state_v1(
        probabilities={"TREND": 0.35, "RANGE": 0.40, "SHOCK": 0.25},
        previous_stable_family="TREND", previous_pending_family=None,
    )
    assert state.stable_family == "TREND"
    assert state.pending_family is None
