from scripts.build_hierarchical_evidence_router_v1 import (
    compatible_regime, evidence_decision, priority_score,
)


def test_lower_hierarchy_never_grants_pass_even_with_80_trades():
    assert evidence_decision(level="STRATEGY", cohort="FRESH_V3_BASE", trades=120,
        expectancy=1, profit_factor=2, cost_ratio=.1)[0] == "DISCOVERY_ONLY"


def test_only_exact_v4_can_be_ready_for_oos():
    assert evidence_decision(level="EXACT_CONTEXT", cohort="FRESH_V5_CONFIRM", trades=80,
        expectancy=.2, profit_factor=1.3, cost_ratio=.1)[0] == "READY_FOR_OOS"


def test_negative_branch_is_stopped_early():
    assert evidence_decision(level="EXACT_CONTEXT", cohort="FRESH_V5_CONFIRM", trades=20,
        expectancy=-.1, profit_factor=.7, cost_ratio=.1)[0] == "EARLY_STOP"


def test_regime_compatibility_is_explicit_not_implicit():
    mapping = {("REGIME", "TREND_UP_HIGH_VOL"): "TREND_HIGH_VOL"}
    assert compatible_regime("trend_up_high_vol", mapping) == "TREND_HIGH_VOL"
    assert compatible_regime("range_low_vol", mapping) == "RANGE_LOW_VOL"


def test_priority_favors_promising_underfilled_branch():
    promising = priority_score(trades=50, expectancy=.2, profit_factor=1.3)
    weak = priority_score(trades=50, expectancy=-.2, profit_factor=.7)
    assert promising > weak
