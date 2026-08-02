from __future__ import annotations
import hashlib,json,os
from math import isclose
import psycopg2,psycopg2.extras

DB=os.getenv("DATABASE_URL","postgresql:///finam_core")
def canonical(value): return json.dumps(value,sort_keys=True,separators=(",",":"),default=str)
def digest(value): return hashlib.sha256(canonical(value).encode()).hexdigest()

def observation_verdict(shadow,paper):
  if not paper: return "NOT_PROVEN"
  pairs=(("side","side"),("entry_price","entry_price"),("fixed_exit_price","exit_price"),
         ("fixed_commission","total_cost"),("fixed_net_pnl","net_pnl"))
  for left,right in pairs:
    if shadow.get(left) is None or paper.get(right) is None: return "NOT_PROVEN"
    if left=="side":
      if str(shadow[left])!=str(paper[right]): return "MISMATCH"
    elif not isclose(float(shadow[left]),float(paper[right]),rel_tol=1e-7,abs_tol=1e-8):
      return "MISMATCH"
  return "MATCH"

def main():
  totals={"MATCH":0,"MISMATCH":0,"NOT_PROVEN":0}
  with psycopg2.connect(DB) as conn,conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as q:
    q.execute("SELECT pg_advisory_xact_lock(hashtext('swing_parity_replay_v1'))")
    q.execute("""SELECT l.process_id,c.strategy_family,c.symbol,c.timeframe,c.frozen_parameter_json,
      c.source_version AS research_code_version,c.criteria_json,i.parameter_snapshot,
      s.parameter_snapshot AS paper_parameter_snapshot,s.status_code AS paper_status,
      rp.policy AS risk_policy
      FROM analytics.swing_candidate_lifecycle_v1 l
      JOIN analytics.swing_shadow_cohort_v1 c ON c.swing_shadow_cohort_id=l.shadow_cohort_id
      JOIN analytics.swing_next_research_plan_item_v1 i ON i.plan_item_id=l.plan_item_id
      LEFT JOIN analytics.swing_paper_strategy_v1 s USING(process_id)
      LEFT JOIN LATERAL(SELECT policy FROM analytics.swing_paper_risk_policy_v1 WHERE active LIMIT 1) rp ON true""")
    for row in map(dict,q.fetchall()):
      base={"spec_version":"SWING_EXECUTION_SPEC_V1","strategy_family":row["strategy_family"],
        "symbol":row["symbol"],"timeframe":row["timeframe"],
        "parameters":row["frozen_parameter_json"],"research_code":row["research_code_version"]}
      frozen_risk=(row["criteria_json"] or {}).get("frozen_risk_policy")
      runtime={**base,"parameters":row["paper_parameter_snapshot"] or row["parameter_snapshot"],
        "risk_policy":row["risk_policy"]}
      research={**base,"risk_policy":frozen_risk}
      spec_verdict=("NOT_PROVEN" if frozen_risk is None else
                    "MATCH" if digest(research)==digest(runtime) else "MISMATCH")
      q.execute("""SELECT o.*,t.* FROM analytics.swing_shadow_observation_v1 o
        LEFT JOIN analytics.swing_paper_trade_v1 t ON t.process_id=%s AND t.entry_ts=o.entry_ts
        WHERE o.swing_shadow_cohort_id=(SELECT shadow_cohort_id FROM analytics.swing_candidate_lifecycle_v1 WHERE process_id=%s)
          AND o.observation_status='CLOSED'""",(row["process_id"],row["process_id"]))
      counts={"MATCH":0,"MISMATCH":0,"NOT_PROVEN":0}
      for item in map(dict,q.fetchall()): counts[observation_verdict(item,item if item.get("trade_id") else None)]+=1
      reasons=([] if spec_verdict=="MATCH" else
        ["FROZEN_RISK_POLICY_MISSING"] if frozen_risk is None else
        ["FROZEN_AND_PAPER_EXECUTION_SPEC_DIFFER"])
      q.execute("""INSERT INTO analytics.swing_parity_v1(process_id,research_spec,research_spec_hash,
        runtime_spec,runtime_spec_hash,spec_verdict,observation_match,observation_mismatch,
        observation_not_proven,reason_codes) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT(process_id) DO UPDATE SET research_spec=excluded.research_spec,
        research_spec_hash=excluded.research_spec_hash,runtime_spec=excluded.runtime_spec,
        runtime_spec_hash=excluded.runtime_spec_hash,spec_verdict=excluded.spec_verdict,
        observation_match=excluded.observation_match,observation_mismatch=excluded.observation_mismatch,
        observation_not_proven=excluded.observation_not_proven,reason_codes=excluded.reason_codes,
        checked_at=clock_timestamp()""",(row["process_id"],psycopg2.extras.Json(research),digest(research),
        psycopg2.extras.Json(runtime),digest(runtime),spec_verdict,counts["MATCH"],counts["MISMATCH"],
        counts["NOT_PROVEN"],psycopg2.extras.Json(reasons)))
      totals[spec_verdict]+=1
  print(" ".join(f"{k.lower()}={v}" for k,v in totals.items()));print("VERDICT=SWING_PARITY_REPLAY_V1_OK");return 0
if __name__=="__main__": raise SystemExit(main())
