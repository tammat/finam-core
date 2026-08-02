from finam_core.research.observation_parity_v1 import compare_observation


def complete():
    return {"features":{"atr_percentile":.5,"relative_volume":1.2,"regime":"TREND",
            "cost_to_atr":.1,"higher_timeframe_aligned":True},"decision":"CONFIRMATION_CLOSE",
            "entry_mode":"CONFIRM_1","side":"LONG","timeframe":"M5","entry_price":100,
            "quantity":1,"exit_price":102,"costs":.1,"net_r":1.1}


def test_complete_identical_observation_matches():
    item=complete(); assert compare_observation(item,item)==("MATCH",[])


def test_material_difference_mismatches():
    left=complete(); right={**left,"net_r":-.5}
    assert compare_observation(left,right)==("MISMATCH",["net_r"])


def test_missing_evidence_is_not_proven():
    left=complete(); right={**left,"exit_price":None}
    verdict,reasons=compare_observation(left,right)
    assert verdict=="NOT_PROVEN" and "exit_price" in reasons
