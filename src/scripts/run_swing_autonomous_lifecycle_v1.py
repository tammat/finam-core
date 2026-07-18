from __future__ import annotations
import json,os,statistics,uuid
from pathlib import Path
import psycopg2,psycopg2.extras
from scripts.run_swing_selection_validation_engine_v1 import trade_rows,metrics
from scripts.run_swing_selection_validation_engine_v1 import COST_BPS
from scripts.swing_execution_contract_v1 import cost_bps,load_swing_execution_contract

DB=os.getenv("DATABASE_URL","postgresql:///finam_core")
NS=uuid.UUID("0904a778-2e91-55a0-b838-56fe9f4ae588")
ROOT=Path(__file__).resolve().parents[2]
POLICY=json.loads((ROOT/"config/research/swing_forward_shadow_policy_v1.json").read_text())
def safe(value): return json.loads(json.dumps(value,default=str))

def forward_result(q,item,result):
  p=item["parameter_snapshot"]; ref=p.get("benchmark") or p.get("source")
  symbols=[item["symbol"]]+([ref] if ref else [])
  q.execute("SELECT symbol,ts,close FROM analytics.swing_market_bars_v1 WHERE timeframe=%s AND symbol=ANY(%s) AND ts>%s ORDER BY ts",(item["timeframe"],symbols,result["holdout_end"]))
  data={s:{} for s in symbols}
  for row in q.fetchall(): data[row["symbol"]][row["ts"]]=float(row["close"])
  timestamps=sorted(set(data[item["symbol"]]).intersection(*(set(data[s]) for s in symbols[1:]))) if ref else sorted(data[item["symbol"]])
  minimum={"H1":120,"H4":40,"D1":20}[item["timeframe"]]
  if len(timestamps)<minimum: return None,{"bars":len(timestamps),"minimum_bars":minimum}
  prices=[data[item["symbol"]][x] for x in timestamps]; refs=[data[ref][x] for x in timestamps] if ref else None
  rows=trade_rows(item["strategy_family"],p,timestamps,prices,refs)
  contract=load_swing_execution_contract(q,item["symbol"])
  exact_cost=float(cost_bps(prices[-1],1,contract)); incremental=max(0.0,exact_cost-float(COST_BPS))
  rows=[(ts,value-incremental) for ts,value in rows]
  n,pf,expectancy=metrics(rows)
  midpoint=len(rows)//2; halves=[metrics(rows[:midpoint]),metrics(rows[midpoint:])] if rows else [(0,0,0),(0,0,0)]
  stable=sum(int(part[0]>=5 and part[1]>=1.0 and part[2]>0) for part in halves)==2
  cumulative=peak=drawdown=max_drawdown=0.0
  for _,value in rows:
    cumulative+=value; peak=max(peak,cumulative); drawdown=peak-cumulative; max_drawdown=max(max_drawdown,drawdown)
  gates={"sample":n>=15,"profit_factor":pf>=1.05,"expectancy":expectancy>0,"stability":stable,
    "drawdown":max_drawdown<=max(250.0,abs(cumulative)),"execution":bool(contract.get("contract_ready"))}
  passed=all(gates.values())
  return passed,{"bars":len(timestamps),"trades":n,"profit_factor":pf,"expectancy":expectancy,
    "max_drawdown_bps":max_drawdown,"gates":gates,"execution_contract":safe(contract),
    "start":timestamps[0].isoformat(),"end":timestamps[-1].isoformat()}

def create_shadow(q,process,item,result,evidence):
  cohort=uuid.uuid5(NS,f"{process['process_id']}:SHADOW")
  candidate=uuid.uuid5(NS,f"{cohort}:{item['hypothesis_id']}")
  criteria={**POLICY,"selection_rule":"FINAL_SWING_OOS_PASS_THEN_FORWARD_PASS","cohort_size":1,"automatic_promotion":True}
  q.execute("""INSERT INTO analytics.swing_shadow_cohort_v1(
    swing_shadow_cohort_id,swing_shadow_candidate_id,factory_run_id,validation_run_id,hypothesis_id,
    strategy_family,symbol,timeframe,frozen_parameter_json,selection_pf,validation_pf,
    validation_expectancy,validation_folds_passed,adjusted_p_value,validation_status,
    observation_not_before,cohort_status,shadow_only,paper_allowed,live_allowed,
    final_oos_opened,criteria_json,source_version)
    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'VALIDATION_PASS',clock_timestamp(),
      'ACCUMULATING',true,false,false,true,%s,'SWING_FINAL_PASS_LIFECYCLE_V1') ON CONFLICT DO NOTHING""",
    (cohort,candidate,process["process_id"],process["process_id"],item["hypothesis_id"],item["strategy_family"],
     item["symbol"],item["timeframe"],psycopg2.extras.Json(item["parameter_snapshot"]),result["profit_factor"],
     evidence["profit_factor"],evidence["expectancy"],result["folds_passed"],result["adjusted_p_value"],psycopg2.extras.Json(criteria)))
  return cohort

def main():
  admitted=forwarded=paper=0
  with psycopg2.connect(DB) as conn:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as q:
      q.execute("SELECT pg_try_advisory_lock(741903147) locked")
      if not q.fetchone()["locked"]: print("VERDICT=SWING_LIFECYCLE_ALREADY_RUNNING"); return 0
      q.execute("""SELECT r.*,i.* FROM analytics.swing_final_oos_result_v1 r
        JOIN analytics.swing_next_research_plan_item_v1 i USING(plan_item_id)
        WHERE r.verdict_code='PASS' AND r.promotion_allowed
          AND NOT EXISTS(SELECT 1 FROM analytics.swing_candidate_lifecycle_v1 l WHERE l.result_id=r.result_id)""")
      for row in q.fetchall():
        process=uuid.uuid5(NS,f"{row['result_id']}:LIFECYCLE")
        q.execute("""INSERT INTO analytics.swing_candidate_lifecycle_v1
          (process_id,result_id,plan_item_id,stage_code,status_code,forward_not_before,gate_evidence)
          VALUES(%s,%s,%s,'FORWARD','WAITING_DATA',%s,%s) ON CONFLICT DO NOTHING""",
          (process,row["result_id"],row["plan_item_id"],row["holdout_end"],psycopg2.extras.Json({"oos_gates":"PASS"})))
        admitted+=q.rowcount
      q.execute("""SELECT l.*,r.*,i.strategy_family,i.symbol,i.timeframe,i.hypothesis_id,i.parameter_snapshot
        FROM analytics.swing_candidate_lifecycle_v1 l JOIN analytics.swing_final_oos_result_v1 r USING(result_id)
        JOIN analytics.swing_next_research_plan_item_v1 i ON i.plan_item_id=l.plan_item_id
        WHERE l.stage_code='FORWARD' AND l.status_code IN ('WAITING_DATA','RUNNING')""")
      for row in q.fetchall():
        passed,evidence=forward_result(q,row,row)
        if passed is None:
          q.execute("UPDATE analytics.swing_candidate_lifecycle_v1 SET progress_pct=least(99,(%s*100/greatest(%s,1))),gate_evidence=%s,heartbeat_at=clock_timestamp(),updated_at=clock_timestamp() WHERE process_id=%s",(evidence["bars"],evidence["minimum_bars"],psycopg2.extras.Json(evidence),row["process_id"])); continue
        if not passed:
          q.execute("UPDATE analytics.swing_candidate_lifecycle_v1 SET status_code='FAIL',progress_pct=100,gate_evidence=%s,reason_codes='[\"FORWARD_FAIL\"]',heartbeat_at=clock_timestamp(),updated_at=clock_timestamp() WHERE process_id=%s",(psycopg2.extras.Json(evidence),row["process_id"])); continue
        cohort=create_shadow(q,row,row,row,evidence)
        q.execute("UPDATE analytics.swing_candidate_lifecycle_v1 SET stage_code='SHADOW',status_code='RUNNING',progress_pct=0,shadow_cohort_id=%s,gate_evidence=%s,heartbeat_at=clock_timestamp(),updated_at=clock_timestamp() WHERE process_id=%s",(cohort,psycopg2.extras.Json(evidence),row["process_id"])); forwarded+=1
      q.execute("SELECT * FROM analytics.swing_candidate_lifecycle_v1 WHERE stage_code='SHADOW' AND status_code='RUNNING'")
      for process in q.fetchall():
        q.execute("""SELECT count(*) FILTER(WHERE observation_status='CLOSED') closed,
          count(DISTINCT date(coalesce(fixed_exit_ts,signal_ts))) sessions,
          coalesce(sum(fixed_net_pnl) FILTER(WHERE fixed_net_pnl>0),0) wins,
          abs(coalesce(sum(fixed_net_pnl) FILTER(WHERE fixed_net_pnl<0),0)) losses,
          coalesce(avg(fixed_net_pnl) FILTER(WHERE observation_status='CLOSED'),0) expectancy,
          coalesce(sum(trailing_net_pnl) FILTER(WHERE trailing_net_pnl>0),0) trailing_wins,
          abs(coalesce(sum(trailing_net_pnl) FILTER(WHERE trailing_net_pnl<0),0)) trailing_losses,
          coalesce(avg(trailing_net_pnl) FILTER(WHERE observation_status='CLOSED'),0) trailing_expectancy,
          count(*) FILTER(WHERE observation_status='CLOSED' AND trailing_exit_ts IS NOT NULL) trailing_complete,
          count(*) FILTER(WHERE broker_order_sent OR runtime_allowed OR execution_enabled) unsafe
          FROM analytics.swing_shadow_observation_v1 WHERE swing_shadow_cohort_id=%s""",(process["shadow_cohort_id"],))
        e=dict(q.fetchone()); required=int(POLICY["minimum_closed_per_timeframe"])
        e["profit_factor"]=float(e["wins"])/float(e["losses"]) if float(e["losses"]) else (999.0 if float(e["wins"]) else 0.0)
        e["trailing_profit_factor"]=float(e["trailing_wins"])/float(e["trailing_losses"]) if float(e["trailing_losses"]) else (999.0 if float(e["trailing_wins"]) else 0.0)
        q.execute("SELECT fixed_net_pnl FROM analytics.swing_shadow_observation_v1 WHERE swing_shadow_cohort_id=%s AND observation_status='CLOSED' ORDER BY fixed_exit_ts",(process["shadow_cohort_id"],))
        cumulative=peak=max_drawdown=0.0
        for row in q.fetchall(): cumulative+=float(row["fixed_net_pnl"] or 0); peak=max(peak,cumulative); max_drawdown=max(max_drawdown,peak-cumulative)
        e["max_drawdown_rub"]=max_drawdown
        progress=min(99,int(int(e["closed"])*100/required))
        if int(e["closed"])<required or int(e["sessions"])<int(POLICY["minimum_trading_sessions"]):
          q.execute("UPDATE analytics.swing_candidate_lifecycle_v1 SET progress_pct=%s,gate_evidence=gate_evidence||%s,heartbeat_at=clock_timestamp(),updated_at=clock_timestamp() WHERE process_id=%s",(progress,psycopg2.extras.Json(safe({"shadow":e})),process["process_id"])); continue
        gates={"sample":int(e["closed"])>=required,"sessions":int(e["sessions"])>=int(POLICY["minimum_trading_sessions"]),
          "fixed_pf":e["profit_factor"]>=float(POLICY["minimum_net_profit_factor"]),"fixed_expectancy":float(e["expectancy"])>float(POLICY["minimum_net_expectancy"]),
          "trailing_complete":int(e["trailing_complete"])==int(e["closed"]),"trailing_pf":e["trailing_profit_factor"]>=float(POLICY["minimum_net_profit_factor"]),
          "drawdown":max_drawdown<=10000.0,"safety":not int(e["unsafe"])}
        e["gates"]=gates; passed=all(gates.values())
        if not passed:
          reasons=[key.upper() for key,value in gates.items() if not value]
          q.execute("UPDATE analytics.swing_candidate_lifecycle_v1 SET status_code='FAIL',progress_pct=100,gate_evidence=gate_evidence||%s,reason_codes=%s,updated_at=clock_timestamp() WHERE process_id=%s",(psycopg2.extras.Json(safe({"shadow":e})),psycopg2.extras.Json(reasons),process["process_id"]));
          q.execute("UPDATE analytics.swing_shadow_cohort_v1 SET cohort_status='FAILED' WHERE swing_shadow_cohort_id=%s",(process["shadow_cohort_id"],)); continue
        admission=uuid.uuid5(NS,f"{process['process_id']}:PAPER")
        q.execute("INSERT INTO analytics.swing_paper_admission_v1(admission_id,process_id,shadow_cohort_id,admission_evidence,paper_allowed) VALUES(%s,%s,%s,%s,true) ON CONFLICT DO NOTHING",(admission,process["process_id"],process["shadow_cohort_id"],psycopg2.extras.Json(safe(e))))
        q.execute("UPDATE analytics.swing_shadow_cohort_v1 SET paper_allowed=true,cohort_status='PASSED' WHERE swing_shadow_cohort_id=%s",(process["shadow_cohort_id"],))
        q.execute("UPDATE analytics.swing_candidate_lifecycle_v1 SET stage_code='PAPER',status_code='READY',progress_pct=100,paper_allowed=true,gate_evidence=gate_evidence||%s,heartbeat_at=clock_timestamp(),updated_at=clock_timestamp() WHERE process_id=%s",(psycopg2.extras.Json(safe({"shadow":e})),process["process_id"])); paper+=1
  print(f"oos_admitted={admitted}"); print(f"forward_pass={forwarded}"); print(f"paper_ready={paper}"); print("live_allowed=0"); print("VERDICT=SWING_AUTONOMOUS_LIFECYCLE_V1_OK"); return 0
if __name__=="__main__": raise SystemExit(main())
