from finam_core.research.execution_spec_v1 import (
    build_execution_spec, compare_specs, execution_spec_hash,
)


def profile():
    return {"candidate_code":"EXPERT_BR_RETEST_VOLUME","entry_mode":"ADAPTIVE",
            "stop_atr":1.6,"take_atr":2.6,"trail_after_r":1.2,"trail_atr":1.0}


def test_hash_is_deterministic_and_numeric_representation_is_normalized():
    left = build_execution_spec(symbol="BRQ6@RTSX",strategy="BR_CONSERVATIVE_BREAKOUT",
        side="SHORT",timeframe="M5",profile=profile(),policy_code="EXPERT_BR")
    right_profile = profile(); right_profile["stop_atr"] = "1.6000"
    right = build_execution_spec(symbol="BRQ6@RTSX",strategy="BR_CONSERVATIVE_BREAKOUT",
        side="SHORT",timeframe="M5",profile=right_profile,policy_code="EXPERT_BR")
    assert execution_spec_hash(left) == execution_spec_hash(right)
    assert compare_specs(left,right) == ("MATCH", [])


def test_difference_and_missing_runtime_fail_closed():
    research = build_execution_spec(symbol="SBER@MISX",strategy="MEAN_REVERSION_EQUITY",
        side="LONG",timeframe="M5",profile={**profile(),"candidate_code":"X"},policy_code="GENERIC")
    runtime = {**research,"exit_policy":"DIFFERENT"}
    assert compare_specs(research,runtime) == ("MISMATCH", ["exit_policy"])
    assert compare_specs(research,{}) == ("NOT_PROVEN", ["SPEC_MISSING"])
