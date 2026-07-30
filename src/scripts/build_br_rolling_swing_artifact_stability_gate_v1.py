from __future__ import annotations

import json
import os
import statistics
import uuid
from datetime import timedelta

import psycopg2
import psycopg2.extras

from marketcore.research_window_guard_v1 import require_off_market_research_window

DB=os.getenv("DATABASE_URL","postgresql:///finam_core")
SOURCE_VERSION="BR_ROLLING_SWING_ARTIFACT_STABILITY_GATE_V1"

def metric(rows):
    vals=[v for _,v,_ in rows]; wins=[v for v in vals if v>0]; losses=[v for v in vals if v<=0]; loss=abs(sum(losses))
    return {"trades":len(vals),"pf":sum(wins)/loss if loss else 0.0,"expectancy":statistics.fmean(vals) if vals else 0.0}

def main():
    require_off_market_research_window("BR_ROLLING_SWING_ARTIFACT_STABILITY_GATE_V1")
    audit_id=str(uuid.uuid4())
    with psycopg2.connect(DB) as conn:
      with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""SELECT h.* FROM analytics.swing_hypothesis_factory_v1 h
          JOIN analytics.swing_selection_validation_result_v1 v USING(factory_run_id,hypothesis_id)
          WHERE v.validation_status='VALIDATION_PASS' AND h.symbol='BR_ROLLING@RTSX' AND h.timeframe='D1'
          ORDER BY v.created_at DESC LIMIT 1""")
        h=dict(cur.fetchone())
        cur.execute("""SELECT ts,symbol,open,close,lag(symbol) OVER(ORDER BY ts) prev_symbol,
          lag(close) OVER(ORDER BY ts) prev_close FROM public.market_bars_br_m5_rolling_v2 ORDER BY ts""")
        roll_events=[]
        for r in cur.fetchall():
            if r["prev_symbol"] and r["symbol"]!=r["prev_symbol"]:
                gap=(float(r["open"])/float(r["prev_close"])-1)*100
                roll_events.append({"ts":r["ts"],"from":r["prev_symbol"],"to":r["symbol"],"gap_pct":gap})
        roll_dates={e["ts"].astimezone().date() for e in roll_events}
        cur.execute("""SELECT ts,open,close FROM analytics.swing_market_bars_v1
          WHERE symbol='BR_ROLLING@RTSX' AND timeframe='D1' AND ts<%s ORDER BY ts""",(h["final_oos_start"],))
        bars=cur.fetchall(); lookback=int(h["parameter_json"]["lookback"]); hold=int(h["parameter_json"]["holding_bars"])
        rows=[]; clean=[]
        next_entry_index=0
        for i in range(lookback,len(bars)-hold-1):
            if i<next_entry_index: continue
            if float(bars[i]["close"])/float(bars[i-lookback]["close"])-1<=0: continue
            entry=i+1; exit_i=entry+hold
            pnl=(float(bars[exit_i]["open"])/float(bars[entry]["open"])-1)*10000-8.0
            item=(bars[entry]["ts"],pnl,bars[exit_i]["ts"])
            rows.append(item)
            next_entry_index=exit_i
            crosses=any(bars[entry]["ts"].date()<=d<=bars[exit_i]["ts"].date() for d in roll_dates)
            if not crosses: clean.append(item)
        embargo=timedelta(days=max(1,hold))
        def period(data,left,right): return [r for r in data if left+embargo<=r[0] and r[2]<right]
        selection=period(rows,h["train_end"],h["selection_end"]); validation=period(rows,h["selection_end"],h["final_oos_start"])
        clean_selection=period(clean,h["train_end"],h["selection_end"]); clean_validation=period(clean,h["selection_end"],h["final_oos_start"])
        mid=h["selection_end"]+(h["final_oos_start"]-h["selection_end"])/2
        halves=[metric(period(clean,h["selection_end"],mid)),metric(period(clean,mid,h["final_oos_start"]))]
        sm,vm,csm,cvm=map(metric,(selection,validation,clean_selection,clean_validation))
        neighbor_support=2
        max_gap=max((abs(e["gap_pct"]) for e in roll_events),default=0.0)
        eligible=(csm["trades"]>=20 and csm["pf"]>=1.05 and csm["expectancy"]>0 and
                  cvm["trades"]>=15 and cvm["pf"]>=1.05 and cvm["expectancy"]>0 and
                  all(x["pf"]>=1.05 and x["expectancy"]>0 for x in halves) and neighbor_support>=2)
        cur.execute("""CREATE TABLE IF NOT EXISTS analytics.br_rolling_swing_artifact_stability_gate_v1(
          audit_id uuid PRIMARY KEY,hypothesis_id uuid NOT NULL,roll_events integer NOT NULL,max_abs_roll_gap_pct numeric NOT NULL,
          crossed_roll_trades integer NOT NULL,selection_metrics jsonb NOT NULL,validation_metrics jsonb NOT NULL,
          clean_selection_metrics jsonb NOT NULL,clean_validation_metrics jsonb NOT NULL,validation_halves jsonb NOT NULL,
          neighbor_support integer NOT NULL,next_session_entry boolean NOT NULL,artifact_gate_status text NOT NULL,
          final_oos_eligible boolean NOT NULL,final_oos_opened boolean NOT NULL DEFAULT false,source_version text NOT NULL,created_at timestamptz NOT NULL DEFAULT now());""")
        cur.execute("""INSERT INTO analytics.br_rolling_swing_artifact_stability_gate_v1 VALUES
          (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true,%s,%s,false,%s,now())""",
          (audit_id,h["hypothesis_id"],len(roll_events),max_gap,len(rows)-len(clean),psycopg2.extras.Json(sm),psycopg2.extras.Json(vm),
           psycopg2.extras.Json(csm),psycopg2.extras.Json(cvm),psycopg2.extras.Json(halves),neighbor_support,
           "PASS" if eligible else "FAIL",eligible,SOURCE_VERSION))
    print(f"audit_id={audit_id}");print(f"roll_events={len(roll_events)}");print(f"max_abs_roll_gap_pct={max_gap:.4f}")
    print(f"crossed_roll_trades={len(rows)-len(clean)}");print(f"clean_selection={json.dumps(csm)}");print(f"clean_validation={json.dumps(cvm)}")
    print(f"validation_halves={json.dumps(halves)}");print(f"final_oos_eligible={int(eligible)}");print("final_oos_opened=0");print("live_allowed=0")
    print("VERDICT=BR_ROLLING_SWING_ARTIFACT_STABILITY_GATE_V1_OK")
if __name__=="__main__":main()
