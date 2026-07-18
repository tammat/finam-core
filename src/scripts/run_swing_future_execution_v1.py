from __future__ import annotations
import hashlib,json,math,os,statistics,uuid
from statistics import NormalDist
import psycopg2,psycopg2.extras
from scripts.run_swing_selection_validation_engine_v1 import trade_rows,metrics

DB=os.getenv("DATABASE_URL","postgresql:///finam_core")
NS=uuid.UUID("42d42cb2-601e-5e17-a890-11b490c922b4")
POLICY={"max_leverage":3.0,"margin_reserve":0.35,"overnight_gap_stress":1.5,"cost_bps":{"H1":12,"H4":18,"D1":25},"roll_required":True}

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
      q.execute("SELECT EXISTS(SELECT 1 FROM analytics.paper_portfolio_mtm_v1 WHERE paper_status='ACTIVE') active")
      active_portfolio=bool(q.fetchone()["active"])
      for i in items:
        q.execute("SELECT ts,close,volume FROM analytics.swing_market_bars_v1 WHERE symbol=%s AND timeframe=%s AND ts>%s ORDER BY ts",(i["symbol"],i["timeframe"],i["confirmation_after_ts"]))
        future=q.fetchall()
        if len(future)<i["minimum_future_bars"]: continue
        active+=1
        q.execute("UPDATE analytics.swing_next_research_plan_item_v1 SET status_code='ACTIVE',activated_at=coalesce(activated_at,clock_timestamp()),updated_at=clock_timestamp() WHERE plan_item_id=%s",(i["plan_item_id"],))
        p=i["parameter_snapshot"]; ref=p.get("benchmark") or p.get("source"); symbols=[i["symbol"]]+([ref] if ref else [])
        q.execute("SELECT symbol,ts,close FROM analytics.swing_market_bars_v1 WHERE timeframe=%s AND symbol=ANY(%s) AND ts>%s ORDER BY ts",(i["timeframe"],symbols,i["confirmation_after_ts"]))
        data={s:{} for s in symbols}
        for r in q.fetchall(): data[r["symbol"]][r["ts"]]=float(r["close"])
        ts=sorted(set(data[i["symbol"]]).intersection(*(set(data[s]) for s in symbols[1:]))) if ref else sorted(data[i["symbol"]])
        prices=[data[i["symbol"]][x] for x in ts]; refs=[data[ref][x] for x in ts] if ref else None
        rows=trade_rows(i["strategy_family"],p,ts,prices,refs); extra=POLICY["cost_bps"][i["timeframe"]]-8
        rows=[(x,v-extra) for x,v in rows]; n,pf,exp=metrics(rows); mid=len(rows)//2
        halves=[metrics(rows[:mid]),metrics(rows[mid:])] if rows else [(0,0,0),(0,0,0)]
        folds=sum(int(x[1]>=1.05 and x[2]>0) for x in halves); vals=[v for _,v in rows]
        z=statistics.fmean(vals)/(statistics.stdev(vals)/math.sqrt(n)) if n>1 and statistics.stdev(vals)>0 else 0
        ap=min(1.0,(1-NormalDist().cdf(z))*max(1,len(items))) if z>0 else 1.0
        stressed=exp-(POLICY["cost_bps"][i["timeframe"]]*.5); cap=statistics.median([float(r["volume"] or 0) for r in future])*float(future[-1]["close"])*.01
        gates={"statistical":ap<=.05,"robustness":folds==2,"holdout":n>=15 and pf>=1.05 and exp>0,"execution":stressed>0,
               "capacity":cap>=500000,"portfolio":not active_portfolio}
        reasons=[k.upper() for k,v in gates.items() if not v]; ok=all(gates.values())
        fp=hashlib.sha256(json.dumps({"item":str(i["plan_item_id"]),"start":ts[0].isoformat(),"end":ts[-1].isoformat(),"p":p},sort_keys=True).encode()).hexdigest()
        rid=uuid.uuid5(NS,fp)
        q.execute("""INSERT INTO analytics.swing_final_oos_result_v1(result_id,plan_item_id,holdout_fingerprint,holdout_start,holdout_end,trades,profit_factor,expectancy,folds_passed,adjusted_p_value,stressed_expectancy,capacity_rub,portfolio_correlation,statistical_pass,robustness_pass,holdout_pass,execution_pass,capacity_pass,portfolio_pass,verdict_code,promotion_allowed,reason_codes,execution_policy)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,%s,%s,%s,%s,%s,%s,%s,false,%s,%s) ON CONFLICT(plan_item_id) DO NOTHING""",
          (rid,i["plan_item_id"],fp,ts[0],ts[-1],n,pf,exp,folds,ap,stressed,cap,gates["statistical"],gates["robustness"],gates["holdout"],gates["execution"],gates["capacity"],gates["portfolio"],"PASS" if ok else "FAIL",psycopg2.extras.Json(reasons),psycopg2.extras.Json(POLICY)))
        q.execute("UPDATE analytics.swing_next_research_plan_item_v1 SET status_code=%s,evaluated_at=clock_timestamp(),updated_at=clock_timestamp() WHERE plan_item_id=%s",("EVALUATED_PASS" if ok else "EVALUATED_FAIL",i["plan_item_id"]))
        evaluated+=1; passed+=int(ok)
      q.execute("SELECT count(*) FROM analytics.swing_next_research_plan_item_v1 WHERE plan_id=%s AND status_code IN ('WAITING_FUTURE_DATA','ACTIVE')",(plan["plan_id"],)); remaining=q.fetchone()["count"]
      q.execute("UPDATE analytics.swing_next_research_plan_v1 SET status_code=%s,heartbeat_at=clock_timestamp(),updated_at=clock_timestamp() WHERE plan_id=%s",("EVALUATED" if not remaining else ("ACTIVE" if active else "WAITING_FUTURE_DATA"),plan["plan_id"]))
  print(f"items_evaluated={evaluated}");print(f"pass={passed}");print("live_allowed=0");print("VERDICT=SWING_FUTURE_EXECUTION_V1_OK");return 0
if __name__=="__main__": raise SystemExit(main())
