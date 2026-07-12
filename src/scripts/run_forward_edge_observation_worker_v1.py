from __future__ import annotations

import os
import statistics
import uuid

import psycopg2
import psycopg2.extras

DB=os.getenv("DATABASE_URL","postgresql:///finam_core")
SOURCE_VERSION="FORWARD_EDGE_OBSERVATION_WORKER_V1"
ROUTED_FAMILIES={"MOMENTUM","BREAKOUT","MEAN_REVERSION"}

def signal(family,params,closes):
    lookback=int(params.get("lookback",20)); current=closes[-1]; window=closes[-lookback-1:-1]
    if len(window)<lookback:return None
    if family=="BREAKOUT": return "LONG" if current>max(window) else ("SHORT" if current<min(window) else None)
    if family=="MOMENTUM":
        change=(current/window[0]-1)*100; threshold=float(params.get("threshold",0.5))*100
        direction=params.get("direction"); side="LONG" if change>=threshold else ("SHORT" if change<=-threshold else None)
        return side if not direction or side==direction else None
    mean=statistics.fmean(window); stdev=statistics.pstdev(window) or 1.0; z=(current-mean)/stdev
    threshold=float(params.get("entry_zscore",params.get("threshold",1.0)))
    return "LONG" if z<=-threshold else ("SHORT" if z>=threshold else None)

def main():
  with psycopg2.connect(DB) as conn:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
      cur.execute("""ALTER TABLE analytics.forward_edge_observation_v1 ADD COLUMN IF NOT EXISTS side text;
        ALTER TABLE analytics.forward_edge_observation_v1 ADD COLUMN IF NOT EXISTS holding_bars integer;
        ALTER TABLE analytics.forward_edge_observation_v1 ADD COLUMN IF NOT EXISTS entry_price numeric;
        ALTER TABLE analytics.forward_edge_observation_v1 ADD COLUMN IF NOT EXISTS exit_price numeric;
        CREATE TABLE IF NOT EXISTS analytics.forward_edge_worker_state_v1(
          cohort_id uuid NOT NULL,incubator_candidate_id uuid NOT NULL,last_evaluated_ts timestamptz,
          worker_status text NOT NULL,last_error text,source_version text NOT NULL,updated_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY(cohort_id,incubator_candidate_id));""")
      cur.execute("SELECT cohort_id FROM analytics.forward_edge_incubator_v1 ORDER BY created_at DESC LIMIT 1"); cohort=cur.fetchone()["cohort_id"]
      cur.execute("SELECT * FROM analytics.forward_edge_incubator_v1 WHERE cohort_id=%s ORDER BY incubator_candidate_id",(cohort,)); candidates=cur.fetchall()
      created=entered=closed=routed=0
      for c in candidates:
        if c["source_kind"]=="SWING_STABILITY_WATCH":continue
        if c["strategy_family"] not in ROUTED_FAMILIES or c["symbol"] in {"MULTI_ASSET@MISX","INTERMARKET_BASKET"}:
          cur.execute("UPDATE analytics.forward_edge_incubator_v1 SET incubator_status='ROUTER_REQUIRED' WHERE cohort_id=%s AND incubator_candidate_id=%s",(cohort,c["incubator_candidate_id"]));routed+=1;continue
        cur.execute("SELECT * FROM analytics.forward_edge_observation_v1 WHERE cohort_id=%s AND incubator_candidate_id=%s AND observation_status IN ('SIGNAL_PENDING_ENTRY','OPEN') ORDER BY signal_ts LIMIT 1",(cohort,c["incubator_candidate_id"])); obs=cur.fetchone()
        cur.execute("SELECT ts,close FROM public.market_bars WHERE symbol=%s AND timeframe=%s ORDER BY ts",(c["symbol"],c["timeframe"])); bars=cur.fetchall()
        if obs and obs["observation_status"]=="SIGNAL_PENDING_ENTRY":
          later=[b for b in bars if b["ts"]>obs["signal_ts"]]
          if later:
            b=later[0];cur.execute("UPDATE analytics.forward_edge_observation_v1 SET entry_ts=%s,entry_price=%s,observation_status='OPEN' WHERE observation_id=%s",(b["ts"],b["close"],obs["observation_id"]));entered+=1;obs=dict(obs);obs.update({"entry_ts":b["ts"],"entry_price":b["close"],"observation_status":"OPEN"})
        if obs and obs["observation_status"]=="OPEN":
          later=[b for b in bars if b["ts"]>obs["entry_ts"]];hold=int(obs["holding_bars"])
          if len(later)>=hold:
            b=later[hold-1];side=1 if obs["side"]=="LONG" else -1;entry=float(obs["entry_price"]);exitp=float(b["close"])
            gross=(exitp-entry)*side;commission=entry*8/10000;net=gross-commission
            cur.execute("UPDATE analytics.forward_edge_observation_v1 SET exit_ts=%s,exit_price=%s,gross_pnl=%s,commission=%s,spread_cost=0,slippage=0,net_pnl=%s,observation_status='CLOSED' WHERE observation_id=%s",(b["ts"],exitp,gross,commission,net,obs["observation_id"]));closed+=1;obs=None
        cur.execute("SELECT last_evaluated_ts FROM analytics.forward_edge_worker_state_v1 WHERE cohort_id=%s AND incubator_candidate_id=%s",(cohort,c["incubator_candidate_id"]));state=cur.fetchone();last=state["last_evaluated_ts"] if state and state["last_evaluated_ts"] else c["observation_not_before"]
        newbars=[b for b in bars if b["ts"]>last]
        if not obs and newbars:
          latest=newbars[-1];idx=next(i for i,b in enumerate(bars) if b["ts"]==latest["ts"]);params=c["frozen_parameter_json"];lookback=int(params.get("lookback",20))
          side=signal(c["strategy_family"],params,[float(b["close"]) for b in bars[max(0,idx-lookback):idx+1]])
          if side:
            cur.execute("""INSERT INTO analytics.forward_edge_observation_v1
              (observation_id,cohort_id,incubator_candidate_id,hypothesis_id,signal_ts,symbol,timeframe,side,holding_bars,
               observation_status,data_quality_status,source_version) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'SIGNAL_PENDING_ENTRY','VERIFIED',%s)""",
              (str(uuid.uuid4()),cohort,c["incubator_candidate_id"],c["hypothesis_id"],latest["ts"],c["symbol"],c["timeframe"],side,int(params.get("holding_bars",params.get("hold",5))),SOURCE_VERSION));created+=1
        latest_ts=bars[-1]["ts"] if bars else last
        cur.execute("""INSERT INTO analytics.forward_edge_worker_state_v1 VALUES(%s,%s,%s,'OK',NULL,%s,now())
          ON CONFLICT(cohort_id,incubator_candidate_id) DO UPDATE SET last_evaluated_ts=excluded.last_evaluated_ts,worker_status='OK',last_error=NULL,source_version=excluded.source_version,updated_at=now()""",(cohort,c["incubator_candidate_id"],latest_ts,SOURCE_VERSION))
  print(f"cohort_id={cohort}");print(f"candidates={len(candidates)}");print(f"router_required={routed}");print(f"signals_created={created}");print(f"entries_created={entered}");print(f"observations_closed={closed}")
  print("orders_created=0");print("paper_created=0");print("live_allowed=0");print("VERDICT=FORWARD_EDGE_OBSERVATION_WORKER_V1_OK")
if __name__=="__main__":main()
