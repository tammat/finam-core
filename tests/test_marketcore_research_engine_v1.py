from scripts.run_marketcore_research_engine_v1 import engine_status

def base(): return dict(frozen_candidates=4,v5_collecting=4,v5_pass=0,v5_fail=0,
 spec_match=0,spec_mismatch=0,spec_not_proven=4,observation_match=0,
 observation_mismatch=0,observation_not_proven=0,swing_candidates=0,
 swing_match=0,swing_mismatch=0,swing_not_proven=0,active_paper_profiles=0)

def test_minimal_engine_status_is_fail_closed():
 assert engine_status(base())=="COLLECTING"
 row=base();row["spec_mismatch"]=1;assert engine_status(row)=="BLOCKED"
 row=base();row.update(v5_collecting=0,v5_pass=1,spec_match=1,spec_not_proven=0)
 assert engine_status(row)=="PASS"

def test_engine_forces_trading_off_and_has_only_evidence_steps():
 source=open("src/scripts/run_marketcore_research_engine_v1.py",encoding="utf-8").read()
 assert 'EXECUTION_ENABLED="0"' in source and 'REAL_TRADING_ENABLED="0"' in source
 assert "run_v5_purged_oos_worker_v1.py" in source
 assert "run_observation_parity_replay_v1.py" in source
