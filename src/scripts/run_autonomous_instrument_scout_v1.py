from __future__ import annotations
import json,os,uuid
from collections import defaultdict
from datetime import datetime,timezone
import psycopg2,psycopg2.extras

DB=os.getenv("DATABASE_URL","postgresql:///finam_core")
SOURCE="AUTONOMOUS_INSTRUMENT_SCOUT_V1"
def category(symbol):
 b=symbol.split("@",1)[0]
 if symbol.endswith("@MISX"):
  if b in {"PLZL","SLVRUB_TOM"}: return "METALS"
  if "RUB" in b or b.startswith(("USD","CNY","EUR")): return "FX"
  if b in {"IMOEX","IMOEX2","RTSI"}: return "INDEX"
  return "EQUITY"
 if b.startswith("BR"): return "OIL"
 if b.startswith("NG"): return "GAS"
 if b.startswith(("GD","GL","SV")) or b in {"PLZL","SLVRUB_TOM"}: return "METALS"
 if "RUB" in b or b.startswith(("USD","CNY","EUR")): return "FX"
 if b in {"IMOEX","IMOEX2","RTSI"}: return "INDEX"
 if symbol.endswith("@MISX"): return "EQUITY"
 return "OTHER"

def main():
 run=str(uuid.uuid4())
 with psycopg2.connect(DB) as conn:
  with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as q:
   q.execute("SELECT pg_try_advisory_lock(941903131) locked")
   if not q.fetchone()["locked"]: print("VERDICT=INSTRUMENT_SCOUT_ALREADY_RUNNING"); return 0
   q.execute("SELECT policy FROM analytics.instrument_scout_policy_v1 WHERE active LIMIT 1"); policy=q.fetchone()["policy"]
   q.execute("""UPDATE analytics.instrument_scout_queue_v1 SET status_code='SUPERSEDED',updated_at=clock_timestamp()
     WHERE status_code='PENDING'""")
   q.execute("INSERT INTO analytics.instrument_scout_run_v1(run_id,status_code) VALUES(%s,'RUNNING')",(run,))
   q.execute("""WITH bars AS(SELECT symbol,count(*) FILTER(WHERE timeframe='M5') bars,max(ts) latest_ts
      FROM public.market_bars GROUP BY symbol), market AS(SELECT DISTINCT ON(symbol) symbol,total_score
      FROM public.moex_top_universe ORDER BY symbol,calculated_at DESC), specs AS(
      SELECT symbol FROM analytics.market_contract_cost_spec_v1 WHERE initial_margin>0 AND buy_sell_fee>=0), rolls AS(
      SELECT DISTINCT ON(root_symbol) current_symbol,next_symbol,selected_symbol FROM analytics.futures_roll_decision_v1
      ORDER BY root_symbol,created_at DESC), catalog AS(
      SELECT symbol,asset_class,instrument_type,market FROM public.instrument_reference
      UNION SELECT symbol,'futures','future','RTSX' FROM rolls r
        CROSS JOIN LATERAL (VALUES(r.current_symbol),(r.next_symbol),(r.selected_symbol)) v(symbol) WHERE symbol IS NOT NULL), deduplicated_catalog AS(
      SELECT DISTINCT ON(symbol) symbol,asset_class,instrument_type,market FROM catalog
      ORDER BY symbol,(instrument_type='future') DESC)
    SELECT i.symbol,coalesce(i.asset_class,i.instrument_type,'') asset_class,coalesce(i.market,split_part(i.symbol,'@',2)) market_code,
      coalesce(b.bars,0) bars,b.latest_ts,coalesce(m.total_score,0) market_score,(s.symbol is not null) spec_ready,
      exists(select 1 from public.market_data_watch_universe w where w.symbol=i.symbol and w.is_enabled) watched,
      (i.symbol NOT LIKE '%%@RTSX' OR EXISTS(SELECT 1 FROM rolls r WHERE i.symbol IN(r.current_symbol,r.next_symbol,r.selected_symbol))) roll_eligible,
      (i.symbol NOT LIKE '%%@RTSX' OR EXISTS(SELECT 1 FROM rolls r WHERE i.symbol=r.selected_symbol)) research_eligible
    FROM deduplicated_catalog i LEFT JOIN bars b USING(symbol) LEFT JOIN market m USING(symbol) LEFT JOIN specs s USING(symbol)
    WHERE (i.symbol LIKE '%%@MISX' AND (i.instrument_type='stock' OR i.asset_class IN('common_share','preferred_share','stock_index','currency','stock_index_pf')))
       OR (i.symbol LIKE '%%@RTSX' AND (i.instrument_type='future' OR i.asset_class='futures'
          OR EXISTS(SELECT 1 FROM public.futures_contract_universe f WHERE f.contract_symbol=i.symbol)))
    ORDER BY i.symbol""")
   rows=[dict(x) for x in q.fetchall()]; now=datetime.now(timezone.utc); minimum=int(policy["min_bars"]); fresh=float(policy["freshness_hours"])
   for x in rows:
    x["category_code"]=category(x["symbol"]); futures=x["symbol"].endswith("@RTSX")
    x["data_ready"]=x["bars"]>=minimum and x["latest_ts"] is not None and (now-x["latest_ts"]).total_seconds()<=fresh*3600 and x["roll_eligible"]
    x["spec_ready"]=(not futures) or bool(x["spec_ready"])
    x["liquidity_ready"]=float(x["market_score"] or 0)>0 or x["bars"]>=minimum
    x["score"]=round(min(40,40*x["bars"]/minimum)+(20 if x["data_ready"] else 0)+(10 if x["spec_ready"] else 0)+min(20,20*float(x["market_score"] or 0))+10,2)
   grouped=defaultdict(list)
   for x in sorted(rows,key=lambda z:(-z["score"],z["symbol"])): grouped[x["category_code"]].append(x)
   selected=set(); quotas=policy["category_quotas"]
   for code in policy["category_order"]:
    eligible=[x for x in grouped[code] if x["data_ready"] and x["spec_ready"] and x["liquidity_ready"] and x["research_eligible"]]
    selected.update(x["symbol"] for x in eligible[:int(quotas.get(code,0))])
   ranks=defaultdict(int); backfill=[]; counts=defaultdict(int)
   for x in sorted(rows,key=lambda z:(z["category_code"],-z["score"],z["symbol"])):
    ranks[x["category_code"]]+=1
    if x["symbol"] in selected: decision,reason,action="SELECTED",["CATEGORY_QUOTA_SELECTED"],"RESEARCH_NEXT"
    elif x["data_ready"] and x["spec_ready"] and not x["research_eligible"]: decision,reason,action="RESERVE",["NEXT_FUTURES_CONTRACT"],"WAIT_ROLL"
    elif x["data_ready"] and x["spec_ready"]: decision,reason,action="RESERVE",["CATEGORY_QUOTA_EXCEEDED"],"KEEP_RESERVE"
    elif x["spec_ready"] and x["roll_eligible"] and not x["data_ready"]: decision,reason,action="BACKFILL",["INSUFFICIENT_OR_STALE_BARS"],"COLLECT_DATA"; backfill.append(x)
    else: decision,reason,action="EXCLUDED",["SPECIFICATION_NOT_READY"],"VERIFY_SPEC"
    counts[decision]+=1
    q.execute("""INSERT INTO analytics.instrument_scout_result_v1(run_id,symbol,category_code,asset_class,market_code,bars,latest_ts,
      market_score,data_ready,spec_ready,liquidity_ready,research_score,category_rank,decision_code,reason_codes,next_action_code)
      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
      (run,x["symbol"],x["category_code"],x["asset_class"],x["market_code"],x["bars"],x["latest_ts"],x["market_score"],x["data_ready"],x["spec_ready"],x["liquidity_ready"],x["score"],ranks[x["category_code"]],decision,psycopg2.extras.Json(reason),action))
   additions=0
   backfill.sort(key=lambda x:(x["watched"],-x["score"],x["symbol"]))
   per_category=defaultdict(int)
   for x in backfill:
    if additions>=int(policy["max_new_watch_symbols_per_run"]): break
    if x["watched"] or per_category[x["category_code"]]>=1: continue
    q.execute("""INSERT INTO public.market_data_watch_universe(symbol,asset_group,timeframe,is_enabled,reason)
      VALUES(%s,%s,'M1',true,%s) ON CONFLICT(symbol) DO NOTHING RETURNING symbol""",(x["symbol"],x["category_code"],SOURCE))
    if q.fetchone():
     additions+=1; per_category[x["category_code"]]+=1
     q.execute("""INSERT INTO analytics.instrument_scout_queue_v1
       (queue_id,run_id,symbol,action_code,status_code,priority,evidence)
       VALUES(%s,%s,%s,'COLLECT_DATA','APPLIED',%s,%s)""",
       (str(uuid.uuid4()),run,x["symbol"],90+additions,
        psycopg2.extras.Json({"source":SOURCE,"reason":"PRIORITY_BACKFILL"})))
   for priority,symbol in enumerate(sorted(selected),1):
    q.execute("""INSERT INTO analytics.instrument_scout_queue_v1(queue_id,run_id,symbol,action_code,priority,evidence)
      VALUES(%s,%s,%s,'RESEARCH_NEXT',%s,%s)""",(str(uuid.uuid4()),run,symbol,priority,psycopg2.extras.Json({"source":SOURCE})))
   q.execute("""UPDATE analytics.instrument_scout_run_v1 SET status_code='COMPLETE',discovered=%s,ready=%s,selected=%s,
      reserve=%s,backfill=%s,excluded=%s,watch_added=%s,finished_at=clock_timestamp() WHERE run_id=%s""",
      (len(rows),counts["SELECTED"]+counts["RESERVE"],counts["SELECTED"],counts["RESERVE"],counts["BACKFILL"],counts["EXCLUDED"],additions,run))
 print(f"discovered={len(rows)} selected={counts['SELECTED']} reserve={counts['RESERVE']} backfill={counts['BACKFILL']} watch_added={additions}")
 print("VERDICT=AUTONOMOUS_INSTRUMENT_SCOUT_V1_OK"); return 0
if __name__=="__main__": raise SystemExit(main())
