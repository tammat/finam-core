from __future__ import annotations

import json
import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "FORWARD_EDGE_RELATION_ROUTER_V1"
TARGETS = ("SBER@MISX", "LKOH@MISX", "GAZP@MISX", "PLZL@MISX")
RELATIONS = (
    ("IMOEX2", "SBER@MISX", 1), ("IMOEX2", "LKOH@MISX", 1), ("IMOEX2", "GAZP@MISX", 1), ("IMOEX2", "PLZL@MISX", 1),
    ("RTSI", "SBER@MISX", 1), ("RTSI", "LKOH@MISX", 1), ("RTSI", "GAZP@MISX", 1), ("RTSI", "PLZL@MISX", 1),
    ("USDRUBF@RTSX", "LKOH@MISX", 1), ("USDRUBF@RTSX", "GAZP@MISX", 1), ("USDRUBF@RTSX", "PLZL@MISX", 1),
    ("BR_ROLLING@RTSX", "LKOH@MISX", 1), ("NG_ROLLING@RTSX", "GAZP@MISX", 1),
)


def bars(cur, symbols):
    normal=[s for s in symbols if s not in {"BR_ROLLING@RTSX","NG_ROLLING@RTSX"}]
    cur.execute("SELECT symbol,ts,close FROM public.market_bars WHERE timeframe='M5' AND symbol=ANY(%s) AND close IS NOT NULL ORDER BY ts", (normal,))
    data = {symbol: {} for symbol in symbols}
    for row in cur.fetchall(): data[row["symbol"]][row["ts"]] = float(row["close"])
    for symbol,table in (("BR_ROLLING@RTSX","market_bars_br_m5_rolling_v2"),("NG_ROLLING@RTSX","market_bars_ng_m5_rolling_v1")):
      if symbol in symbols:
        cur.execute(f"SELECT ts,close FROM public.{table} WHERE close IS NOT NULL ORDER BY ts")
        for row in cur.fetchall(): data[symbol][row["ts"]]=float(row["close"])
    return data


def common(data, symbols):
    return sorted(set.intersection(*(set(data[s]) for s in symbols)))


def main():
  with psycopg2.connect(DB) as conn:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
      cur.execute("""ALTER TABLE analytics.forward_edge_observation_v1 ADD COLUMN IF NOT EXISTS planned_entry_ts timestamptz;
        ALTER TABLE analytics.forward_edge_observation_v1 ADD COLUMN IF NOT EXISTS signal_context jsonb;""")
      cur.execute("SELECT cohort_id FROM analytics.forward_edge_incubator_v1 ORDER BY created_at DESC LIMIT 1"); cohort=cur.fetchone()["cohort_id"]
      cur.execute("SELECT * FROM analytics.forward_edge_incubator_v1 WHERE cohort_id=%s AND incubator_status='ROUTER_REQUIRED' ORDER BY strategy_family",(cohort,)); candidates=cur.fetchall()
      created=entered=closed=0
      for c in candidates:
        params=c["frozen_parameter_json"]; family=c["strategy_family"]
        symbols=(TARGETS+(params["benchmark"],)) if family=="RELATIVE_STRENGTH" else tuple(sorted({x for r in RELATIONS for x in r[:2]}))
        data=bars(cur,symbols); timestamps=common(data,symbols)
        if not timestamps: continue
        cur.execute("SELECT * FROM analytics.forward_edge_observation_v1 WHERE cohort_id=%s AND incubator_candidate_id=%s AND observation_status IN ('SIGNAL_PENDING_ENTRY','OPEN') ORDER BY signal_ts LIMIT 1",(cohort,c["incubator_candidate_id"])); obs=cur.fetchone()
        if obs and obs["observation_status"]=='SIGNAL_PENDING_ENTRY':
          entry_ts=next((ts for ts in timestamps if ts>=obs["planned_entry_ts"]),None)
          if entry_ts:
            context=json.loads(obs["signal_context"] or "{}")
            legs=context["legs"]
            for leg in legs: leg["entry_price"]=data[leg["target"]][entry_ts]
            cur.execute("UPDATE analytics.forward_edge_observation_v1 SET entry_ts=%s,entry_price=%s,signal_context=%s::jsonb,observation_status='OPEN' WHERE observation_id=%s",(entry_ts,sum(x["entry_price"] for x in legs)/len(legs),json.dumps(context),obs["observation_id"]));entered+=1;obs=None
        if obs and obs["observation_status"]=='OPEN':
          index=timestamps.index(obs["entry_ts"]); hold=int(obs["holding_bars"])
          if index+hold < len(timestamps):
            exit_ts=timestamps[index+hold]; context=json.loads(obs["signal_context"]); legs=context["legs"]
            gross=sum((data[x["target"]][exit_ts]/x["entry_price"]-1)*x["side"] for x in legs)/len(legs)
            avg_entry=sum(x["entry_price"] for x in legs)/len(legs); commission=avg_entry*8/10000; net=gross*avg_entry-commission
            cur.execute("UPDATE analytics.forward_edge_observation_v1 SET exit_ts=%s,exit_price=%s,gross_pnl=%s,commission=%s,spread_cost=0,slippage=0,net_pnl=%s,observation_status='CLOSED' WHERE observation_id=%s",(exit_ts,avg_entry*(1+gross),gross*avg_entry,commission,net,obs["observation_id"]));closed+=1;obs=None
        cur.execute("SELECT last_evaluated_ts FROM analytics.forward_edge_worker_state_v1 WHERE cohort_id=%s AND incubator_candidate_id=%s",(cohort,c["incubator_candidate_id"])); state=cur.fetchone(); cutoff=state["last_evaluated_ts"] if state else c["observation_not_before"]
        latest=timestamps[-1]
        if not obs and latest>cutoff and latest>=c["observation_not_before"]:
          legs=[]; planned=None
          if family=='RELATIVE_STRENGTH':
            lookback=int(params["lookback"]); i=len(timestamps)-1
            if i>=lookback:
              benchmark=params["benchmark"]; values=sorted(((data[s][latest]/data[s][timestamps[i-lookback]]-1)-(data[benchmark][latest]/data[benchmark][timestamps[i-lookback]]-1),s) for s in TARGETS)
              threshold=float(params["rank_threshold"]); denom=max(1,len(values)-1)
              legs=[{"target":s,"side":1 if rank/denom>=threshold else -1} for rank,(_,s) in enumerate(values) if rank/denom>=threshold or rank/denom<=1-threshold]
              planned=timestamps[i+1] if i+1<len(timestamps) else None
          else:
            impulse=int(params["impulse_bars"]); lag=int(params["lag_bars"]); i=len(timestamps)-1
            if i>=impulse and i+lag<len(timestamps):
              for source,target,direction in RELATIONS:
                move=data[source][latest]/data[source][timestamps[i-impulse]]-1
                if abs(move)>=float(params["threshold"]): legs.append({"target":target,"side":(1 if move>0 else -1)*direction,"source":source})
              planned=timestamps[i+lag]
          if legs and planned:
            cur.execute("""INSERT INTO analytics.forward_edge_observation_v1(observation_id,cohort_id,incubator_candidate_id,hypothesis_id,signal_ts,planned_entry_ts,symbol,timeframe,side,holding_bars,signal_context,observation_status,data_quality_status,source_version)
              VALUES(%s,%s,%s,%s,%s,%s,%s,'M5','BASKET',%s,%s::jsonb,'SIGNAL_PENDING_ENTRY','VERIFIED',%s)""",(str(uuid.uuid4()),cohort,c["incubator_candidate_id"],c["hypothesis_id"],latest,planned,c["symbol"],int(params["holding_bars"]),json.dumps({"legs":legs}),SOURCE_VERSION));created+=1
        cur.execute("""INSERT INTO analytics.forward_edge_worker_state_v1 VALUES(%s,%s,%s,'OK',NULL,%s,now()) ON CONFLICT(cohort_id,incubator_candidate_id) DO UPDATE SET last_evaluated_ts=excluded.last_evaluated_ts,worker_status='OK',last_error=NULL,source_version=excluded.source_version,updated_at=now()""",(cohort,c["incubator_candidate_id"],latest,SOURCE_VERSION))
        cur.execute("UPDATE analytics.forward_edge_incubator_v1 SET incubator_status='ACCUMULATING' WHERE cohort_id=%s AND incubator_candidate_id=%s",(cohort,c["incubator_candidate_id"]))
  print(f"cohort_id={cohort}");print(f"routed_candidates={len(candidates)}");print(f"signals_created={created}");print(f"entries_created={entered}");print(f"observations_closed={closed}");print("orders_created=0");print("paper_created=0");print("live_allowed=0");print("VERDICT=FORWARD_EDGE_RELATION_ROUTER_V1_OK")
if __name__=='__main__':main()
