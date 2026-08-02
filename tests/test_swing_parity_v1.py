from scripts.run_swing_parity_replay_v1 import observation_verdict

def test_swing_observation_match_and_mismatch():
    shadow={"side":"LONG","entry_price":100,"fixed_exit_price":105,"fixed_commission":2,"fixed_net_pnl":3}
    paper={"side":"LONG","entry_price":100,"exit_price":105,"total_cost":2,"net_pnl":3}
    assert observation_verdict(shadow,paper)=="MATCH"
    assert observation_verdict(shadow,{**paper,"net_pnl":-3})=="MISMATCH"
    assert observation_verdict(shadow,None)=="NOT_PROVEN"

def test_swing_lifecycle_requires_parity_before_paper():
    source=open("src/scripts/run_swing_autonomous_lifecycle_v1.py",encoding="utf-8").read()
    assert "analytics.swing_parity_v1" in source
    assert 'parity["spec_verdict"]!="MATCH"' in source
