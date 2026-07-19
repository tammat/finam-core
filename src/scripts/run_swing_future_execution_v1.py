from __future__ import annotations
import hashlib,json,math,os,statistics,uuid
from collections import defaultdict
from statistics import NormalDist
import psycopg2,psycopg2.extras
from scripts.run_swing_selection_validation_engine_v1 import COST_BPS,trade_rows,metrics
from scripts.evaluate_edge_methodology_contract_v1 import correlation,portfolio_daily_pnl
from scripts.swing_execution_contract_v1 import cost_bps,load_swing_execution_contract

DB=os.getenv("DATABASE_URL","postgresql:///finam_core")
NS=uuid.UUID("42d42cb2-601e-5e17-a890-11b490c922b4")
POLICY={"overnight_gap_stress":1.5,"commission_bps":8.0,"roll_required":True}

def json_safe(value): return json.loads(json.dumps(value,default=str))

def daily_pnl(rows):
  result=defaultdict(float)
  for ts,value in rows: result[ts.date().isoformat()]+=float(value)
  return dict(result)

def execution_evidence(q,item,future):
  symbol=item["symbol"]
  root="BR" if symbol.startswith("BR") else ("NG" if symbol.startswith("NG") else None)
  context=load_swing_execution_contract(q,symbol); roll=context.get("roll_decision")
  execution_symbol=context["execution_symbol"]
  gaps=[]
  for previous,current in zip(future,future[1:]):
    close=float(previous["close"] or 0); opened=float(current.get("open") or current["close"] or 0)
    if close>0: gaps.append(abs(opened/close-1)*10000)
  gap_bps=statistics.median(gaps) if gaps else 0.0
  exact_cost=float(cost_bps(float(future[-1]["close"]),1,context))
  total_bps=exact_cost+gap_bps*POLICY["overnight_gap_stress"]
  spec_ready=bool(context.get("contract_ready"))
  margin_ready=(not root) or float(context.get("initial_margin_rub",0))>0
  roll_ready=(not root) or bool(roll and roll["selected_symbol"])
  carry_ready=(not root) or bool(roll and str(roll["decision_code"]).startswith("KEEP_"))
  carry_bps=0.0 if carry_ready else None
  return {**context,"research_symbol":symbol,"execution_symbol":execution_symbol,"round_trip_cost_bps":exact_cost,
    "median_gap_bps":gap_bps,"total_stress_cost_bps":total_bps,"spec_ready":spec_ready,
    "margin_ready":margin_ready,"roll_ready":roll_ready,"carry_ready":carry_ready,"carry_bps":carry_bps,
    "carry_source":"NOT_APPLICABLE_KEEP_CONTRACT" if carry_ready else "MISSING_ROLL_BASIS",
    "roll_decision":dict(roll) if roll else None}

def main():
  with psycopg2.connect(DB) as c:
    with c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as q:
      q.execute("SELECT pg_try_advisory_lock(741903146) locked")
      if not q.fetchone()["locked"]: print("VERDICT=SWING_FUTURE_EXECUTION_ALREADY_RUNNING"); return 0
      q.execute("SELECT * FROM analytics.swing_next_research_plan_v1 WHERE status_code IN ('WAITING_FUTURE_DATA','ACTIVE') ORDER BY created_at LIMIT 1")
      plan=q.fetchone()
      if not plan: print("VERDICT=SWING_FUTURE_EXECUTION_IDLE"); return 0
      q.execute("UPDATE analytics.swing_next_research_plan_v1 SET heartbeat_at=clock_timestamp(),attempt_count=attempt_count+1,last_error_code=NULL WHERE plan_id=%s",(plan["plan_id"],))
      q.execute("SELECT * FROM analytics.swing_next_research_plan_item_v1 WHERE plan_id=%s AND status_code IN ('WAITING_FUTURE_DATA','ACTIVE') ORDER BY priority",(plan["plan_id"],))
      items=q.fetchall(); evaluated=passed=active=0
      q.execute("SELECT policy FROM analytics.edge_methodology_contract_v1 WHERE active LIMIT 1")
      methodology=(q.fetchone() or {}).get("policy") or {}
      portfolio,active_portfolio=portfolio_daily_pnl(q)
      for i in items:
        q.execute("SELECT ts,open,close,volume FROM analytics.swing_market_bars_v1 WHERE symbol=%s AND timeframe=%s AND ts>%s ORDER BY ts",(i["symbol"],i["timeframe"],i["confirmation_after_ts"]))
        future=q.fetchall()
        if len(future)<i["minimum_future_bars"]: continue
        active+=1
        q.execute("UPDATE analytics.swing_next_research_plan_item_v1 SET status_code='ACTIVE',activated_at=coalesce(activated_at,clock_timestamp()),updated_at=clock_timestamp() WHERE plan_item_id=%s",(i["plan_item_id"],))
        p=i["parameter_snapshot"]; ref=p.get("benchmark") or p.get("source"); symbols=[i["symbol"]]+([ref] if ref else [])
        q.execute("SELECT symbol,ts,close,coalesce(volume,0) volume FROM analytics.swing_market_bars_v1 WHERE timeframe=%s AND symbol=ANY(%s) AND ts>%s ORDER BY ts",(i["timeframe"],symbols,i["confirmation_after_ts"]))
        data={s:{} for s in symbols}; volume_data={s:{} for s in symbols}
        for r in q.fetchall():
          data[r["symbol"]][r["ts"]]=float(r["close"]); volume_data[r["symbol"]][r["ts"]]=float(r["volume"])
        ts=sorted(set(data[i["symbol"]]).intersection(*(set(data[s]) for s in symbols[1:]))) if ref else sorted(data[i["symbol"]])
        prices=[data[i["symbol"]][x] for x in ts]; refs=[data[ref][x] for x in ts] if ref else None
        volumes=[volume_data[i["symbol"]][x] for x in ts]
        rows=trade_rows(i["strategy_family"],p,ts,prices,refs,volumes)
        execution=execution_evidence(q,i,future)
        incremental_cost=max(0.0,float(execution["total_stress_cost_bps"])-float(COST_BPS))
        rows=[(x,v-incremental_cost) for x,v in rows]; n,pf,exp=metrics(rows); mid=len(rows)//2
        halves=[metrics(rows[:mid]),metrics(rows[mid:])] if rows else [(0,0,0),(0,0,0)]
        folds=sum(int(x[1]>=1.05 and x[2]>0) for x in halves); vals=[v for _,v in rows]
        z=statistics.fmean(vals)/(statistics.stdev(vals)/math.sqrt(n)) if n>1 and statistics.stdev(vals)>0 else 0
        ap=min(1.0,(1-NormalDist().cdf(z))*max(1,len(items))) if z>0 else 1.0
        stressed=exp; cap=statistics.median([float(r["volume"] or 0) for r in future])*float(future[-1]["close"])*float(execution.get("max_participation_rate",.01))
        portfolio_corr,overlap=correlation(daily_pnl(rows),portfolio)
        portfolio_ok=(not active_portfolio) or (overlap>=int(methodology.get("min_portfolio_overlap_days",20)) and portfolio_corr is not None and abs(portfolio_corr)<=float(methodology.get("max_portfolio_abs_correlation",.75)))
        gates={"statistical":ap<=float(methodology.get("max_fdr_q",.10)),"robustness":folds==2,"holdout":n>=15 and pf>=1.05 and exp>0,
               "execution":stressed>0 and execution["spec_ready"] and execution["margin_ready"] and execution["roll_ready"] and execution["carry_ready"],
               "capacity":cap>=float(methodology.get("min_capacity_rub",500000)),"portfolio":portfolio_ok}
        reasons=[k.upper() for k,v in gates.items() if not v]; ok=all(gates.values())
        fp=hashlib.sha256(json.dumps({"item":str(i["plan_item_id"]),"start":ts[0].isoformat(),"end":ts[-1].isoformat(),"p":p},sort_keys=True).encode()).hexdigest()
        rid=uuid.uuid5(NS,fp)
        q.execute("""INSERT INTO analytics.swing_final_oos_result_v1(result_id,plan_item_id,holdout_fingerprint,holdout_start,holdout_end,trades,profit_factor,expectancy,folds_passed,adjusted_p_value,stressed_expectancy,capacity_rub,portfolio_correlation,statistical_pass,robustness_pass,holdout_pass,execution_pass,capacity_pass,portfolio_pass,verdict_code,promotion_allowed,reason_codes,execution_policy)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(plan_item_id) DO NOTHING""",
          (rid,i["plan_item_id"],fp,ts[0],ts[-1],n,pf,exp,folds,ap,stressed,cap,portfolio_corr,gates["statistical"],gates["robustness"],gates["holdout"],gates["execution"],gates["capacity"],gates["portfolio"],"PASS" if ok else "FAIL",ok,psycopg2.extras.Json(reasons),psycopg2.extras.Json(json_safe({**execution,"portfolio_overlap_days":overlap}))))
        q.execute("UPDATE analytics.swing_next_research_plan_item_v1 SET status_code=%s,evaluated_at=clock_timestamp(),updated_at=clock_timestamp() WHERE plan_item_id=%s",("EVALUATED_PASS" if ok else "EVALUATED_FAIL",i["plan_item_id"]))
        evaluated+=1; passed+=int(ok)
      q.execute("SELECT count(*) FROM analytics.swing_next_research_plan_item_v1 WHERE plan_id=%s AND status_code IN ('WAITING_FUTURE_DATA','ACTIVE')",(plan["plan_id"],)); remaining=q.fetchone()["count"]
      q.execute("UPDATE analytics.swing_next_research_plan_v1 SET status_code=%s,heartbeat_at=clock_timestamp(),updated_at=clock_timestamp() WHERE plan_id=%s",("EVALUATED" if not remaining else ("ACTIVE" if active else "WAITING_FUTURE_DATA"),plan["plan_id"]))
  print(f"items_evaluated={evaluated}");print(f"pass={passed}");print("live_allowed=0");print("VERDICT=SWING_FUTURE_EXECUTION_V1_OK");return 0
if __name__=="__main__": raise SystemExit(main())
