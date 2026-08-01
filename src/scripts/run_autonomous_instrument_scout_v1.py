from __future__ import annotations

import math
import os
import statistics
import uuid
from collections import defaultdict
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras


DB=os.getenv("DATABASE_URL","postgresql:///finam_core")
SOURCE="TRADABLE_VOLATILITY_SCOUT_V3"


def category(symbol: str) -> str:
    base=symbol.split("@",1)[0]
    if base.startswith("BR"): return "OIL"
    if base.startswith("NG"): return "GAS"
    if base.startswith(("GD","GL","SV")) or base in {"PLZL","SLVRUB_TOM"}: return "METALS"
    if "RUB" in base or base.startswith(("USD","CNY","EUR")): return "FX"
    if base in {"IMOEX","IMOEX2","RTSI"}: return "INDEX"
    if symbol.endswith("@MISX"): return "EQUITY"
    return "OTHER"


def correlation(left: dict, right: dict) -> float:
    keys=sorted(set(left).intersection(right))
    if len(keys)<60: return 0.0
    xs=[left[k] for k in keys]; ys=[right[k] for k in keys]
    mx,my=statistics.fmean(xs),statistics.fmean(ys)
    dx=[x-mx for x in xs]; dy=[y-my for y in ys]
    denom=math.sqrt(sum(x*x for x in dx)*sum(y*y for y in dy))
    return sum(x*y for x,y in zip(dx,dy))/denom if denom else 0.0


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def percentile_rank(values: list[float], value: float) -> float:
    return 100.0 * sum(item <= value for item in values) / len(values) if values else 0.0


def volatility_features(bars: list[dict]) -> dict:
    """Causal, scale-free M5 volatility and tradability features."""
    valid=[item for item in bars if float(item.get("close") or 0)>0]
    if len(valid)<65:
        return {"atr_pct":0.0,"atr_percentile":0.0,"rv20":0.0,"rv60":0.0,
                "volatility_acceleration":0.0,"volume_zscore":0.0,
                "directional_efficiency":0.0,"volatility_persistence":0.0,
                "zero_volume_share":1.0}
    closes=[float(item["close"]) for item in valid]
    volumes=[float(item.get("volume") or 0) for item in valid]
    returns=[closes[i]/closes[i-1]-1 for i in range(1,len(closes)) if closes[i-1]>0]
    true_ranges=[]
    for index in range(1,len(valid)):
        previous=closes[index-1]
        high=float(valid[index].get("high") or closes[index])
        low=float(valid[index].get("low") or closes[index])
        true_ranges.append(max(high-low,abs(high-previous),abs(low-previous))/previous)
    atr_windows=[statistics.fmean(true_ranges[i-20:i]) for i in range(20,len(true_ranges)+1)]
    atr=statistics.fmean(true_ranges[-20:])
    rv20=statistics.pstdev(returns[-20:])
    rv60=statistics.pstdev(returns[-60:])
    historical_volume=volumes[-120:-20]
    volume_mean=statistics.fmean(historical_volume) if historical_volume else 0.0
    volume_std=statistics.pstdev(historical_volume) if len(historical_volume)>1 else 0.0
    recent_volume=statistics.fmean(volumes[-20:])
    volume_z=(recent_volume-volume_mean)/volume_std if volume_std>0 else 0.0
    recent_closes=closes[-21:]
    path=sum(abs(recent_closes[i]-recent_closes[i-1]) for i in range(1,len(recent_closes)))
    efficiency=abs(recent_closes[-1]-recent_closes[0])/path if path>0 else 0.0
    prior_abs=sorted(abs(item) for item in returns[-120:-20])
    baseline=prior_abs[len(prior_abs)//2] if prior_abs else 0.0
    persistence=sum(abs(item)>baseline for item in returns[-20:])/20 if baseline>0 else 0.0
    return {"atr_pct":atr*100.0,"atr_percentile":percentile_rank(atr_windows[:-1],atr),
            "rv20":rv20*100.0,"rv60":rv60*100.0,
            "volatility_acceleration":rv20/max(rv60,1e-12),"volume_zscore":volume_z,
            "directional_efficiency":efficiency,"volatility_persistence":persistence,
            "zero_volume_share":sum(volume<=0 for volume in volumes[-60:])/60}


def tradable_volatility_score(item: dict) -> float:
    liquidity_quality=clamp(100.0*(1.0-float(item.get("spread_atr_ratio") or 0)))
    acceleration=clamp((float(item.get("volatility_acceleration") or 0)-0.8)/1.2*100)
    volume_score=clamp(50.0+15.0*float(item.get("volume_zscore") or 0))
    score=(.30*float(item.get("atr_percentile") or 0)+.20*acceleration+
           .15*volume_score+.15*100*float(item.get("directional_efficiency") or 0)+
           .10*100*float(item.get("volatility_persistence") or 0)+.10*liquidity_quality)
    score-=50.0*float(item.get("zero_volume_share") or 0)
    if float(item.get("volatility_acceleration") or 0)>3 and float(item.get("volume_zscore") or 0)>5:
        score-=15.0
    return clamp(score)


def add_event(q,run,symbol,order,stage,verdict,reason,score=None,evidence=None):
    q.execute("""INSERT INTO analytics.instrument_scout_funnel_event_v2
      (run_id,symbol,stage_order,stage_code,verdict_code,score,reason_code,evidence)
      VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
      (run,symbol,order,stage,verdict,score,reason,psycopg2.extras.Json(evidence or {})))


def main() -> int:
    run=str(uuid.uuid4())
    with psycopg2.connect(DB) as conn:
      with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as q:
        q.execute("SELECT pg_try_advisory_lock(941903131) locked")
        if not q.fetchone()["locked"]: print("VERDICT=INSTRUMENT_SCOUT_ALREADY_RUNNING"); return 0
        q.execute("SELECT policy FROM analytics.instrument_scout_policy_v1 WHERE active LIMIT 1")
        policy=q.fetchone()["policy"]
        q.execute("""UPDATE analytics.instrument_scout_queue_v1 SET status_code='SUPERSEDED',updated_at=clock_timestamp()
          WHERE status_code='PENDING'""")
        q.execute("INSERT INTO analytics.instrument_scout_run_v1(run_id,status_code) VALUES(%s,'RUNNING')",(run,))
        q.execute("""WITH bars AS(
           SELECT symbol,count(*) FILTER(WHERE timeframe='M5') bars,max(ts) latest_ts,
             percentile_cont(.5) WITHIN GROUP(ORDER BY volume) FILTER(WHERE timeframe='M5' AND volume>0) median_volume,
             percentile_cont(.5) WITHIN GROUP(ORDER BY close*volume) FILTER(WHERE timeframe='M5' AND close>0 AND volume>0) median_turnover
           FROM public.market_bars GROUP BY symbol), market AS(
           SELECT DISTINCT ON(symbol) symbol,total_score FROM public.moex_top_universe ORDER BY symbol,calculated_at DESC), specs AS(
           SELECT symbol,coalesce(nullif((source_payload->>'STEPPRICE')::numeric,0)/
             nullif((source_payload->>'MINSTEP')::numeric,0),1) contract_multiplier
           FROM analytics.market_contract_cost_spec_v1 WHERE initial_margin>0 AND buy_sell_fee>=0), spread AS(
           SELECT DISTINCT ON(symbol) symbol,avg_spread_bps FROM analytics.market_microstructure_aggregate_v1
           WHERE bucket_ts>=clock_timestamp()-interval '7 days' ORDER BY symbol,bucket_ts DESC), rolls AS(
           SELECT DISTINCT ON(root_symbol) root_symbol,current_symbol,next_symbol,selected_symbol
           FROM analytics.futures_roll_decision_v1 ORDER BY root_symbol,created_at DESC), catalog AS(
           SELECT symbol,asset_class,instrument_type,market,source provider_code FROM public.instrument_reference
           UNION ALL SELECT symbol,asset_class,asset_class,exchange_code,source_version FROM analytics.market_instrument_v1 WHERE is_active
           UNION ALL SELECT symbol,asset_class,asset_class,board,source FROM public.moex_top_universe
           UNION ALL SELECT symbol,'market_bars','observed',split_part(symbol,'@',2),'MARKET_BARS' FROM bars
           UNION ALL SELECT symbol,'futures','future','RTSX','FUTURES_ROLL' FROM rolls r
             CROSS JOIN LATERAL(values(r.current_symbol),(r.next_symbol),(r.selected_symbol)) v(symbol) WHERE symbol IS NOT NULL), dedup AS(
           SELECT DISTINCT ON(symbol) * FROM catalog WHERE symbol IS NOT NULL ORDER BY symbol,(instrument_type='future') DESC)
         SELECT i.symbol,coalesce(i.asset_class,i.instrument_type,'') asset_class,
          coalesce(i.market,split_part(i.symbol,'@',2)) market_code,i.provider_code,
          coalesce(b.bars,0) bars,b.latest_ts,coalesce(b.median_volume,0) median_volume,
          coalesce(b.median_turnover,0)*coalesce(s.contract_multiplier,1)*.01 capacity_rub,coalesce(m.total_score,0) market_score,
          (s.symbol IS NOT NULL) spec_ready,sp.avg_spread_bps,
          EXISTS(SELECT 1 FROM public.market_data_watch_universe w WHERE w.symbol=i.symbol AND w.is_enabled) watched,
          (i.symbol NOT LIKE '%%@RTSX' OR EXISTS(SELECT 1 FROM rolls r WHERE i.symbol IN(r.current_symbol,r.next_symbol,r.selected_symbol))) roll_eligible,
          (i.symbol NOT LIKE '%%@RTSX' OR EXISTS(SELECT 1 FROM rolls r WHERE i.symbol=r.selected_symbol)) research_eligible
         FROM dedup i LEFT JOIN bars b USING(symbol) LEFT JOIN market m USING(symbol)
          LEFT JOIN specs s USING(symbol) LEFT JOIN spread sp USING(symbol)
         WHERE i.symbol LIKE '%%@MISX' OR i.symbol LIKE '%%@RTSX' OR i.symbol IN('BTCUSD','ETHUSD')
         ORDER BY i.symbol""")
        rows=[dict(x) for x in q.fetchall()]
        now=datetime.now(timezone.utc); minimum=int(policy["min_bars"]); fresh=float(policy["freshness_hours"])
        q.execute("""SELECT symbol,ts,open,high,low,close,volume FROM (
          SELECT symbol,ts,open,high,low,close,volume,row_number() over(partition by symbol order by ts desc) n
          FROM public.market_bars WHERE timeframe='M5' AND close>0
            AND source NOT IN ('unknown','synthetic_futures_backfill_v1')) x
          WHERE n<=%s ORDER BY symbol,ts""",(int(policy["correlation_bars"]),))
        bars_by_symbol=defaultdict(list); prices=defaultdict(list)
        for item in q.fetchall():
            bars_by_symbol[item["symbol"]].append(dict(item))
            prices[item["symbol"]].append((item["ts"],float(item["close"])))
        returns={}
        for symbol,values in prices.items():
            returns[symbol]={values[i][0]:values[i][1]/values[i-1][1]-1 for i in range(1,len(values)) if values[i-1][1]>0}
        for x in rows:
            x["category_code"]=category(x["symbol"]); futures=x["symbol"].endswith("@RTSX")
            age=(now-x["latest_ts"]).total_seconds()/60 if x["latest_ts"] else None
            x["freshness_age_minutes"]=age; x["history_ready"]=x["bars"]>=minimum
            x["data_ready"]=x["history_ready"] and age is not None and age<=fresh*60 and x["roll_eligible"]
            x["spec_ready"]=(not futures) or bool(x["spec_ready"])
            x["spread_source"]="ORDER_BOOK" if x["avg_spread_bps"] is not None else "COST_MODEL_ESTIMATE"
            x["effective_spread_bps"]=float(x["avg_spread_bps"] if x["avg_spread_bps"] is not None else (20 if x["symbol"].endswith("USD") else 8))
            x["liquidity_ready"]=(float(x["median_volume"] or 0)>=float(policy["min_median_volume"])
              and float(x["capacity_rub"] or 0)>=float(policy["min_capacity_rub"])
              and x["effective_spread_bps"]<=float(policy["max_spread_bps"]))
            x.update(volatility_features(bars_by_symbol.get(x["symbol"],[])))
            x["spread_atr_ratio"]=x["effective_spread_bps"]/max(float(x["atr_pct"])*100.0,1e-9)
            x["tradable_volatility_score"]=tradable_volatility_score(x)
            x["regime_novelty_score"]=clamp(abs(x["volatility_acceleration"]-1)*50.0)
            x["tradable_volatility_ready"]=(x["liquidity_ready"]
              and x["atr_pct"]>=float(policy["min_atr_pct"])
              and x["zero_volume_share"]<=float(policy["max_zero_volume_share"])
              and x["spread_atr_ratio"]<=float(policy["max_spread_atr_ratio"])
              and x["tradable_volatility_score"]>=float(policy["min_tradable_volatility_score"]))
            x["candidate_stage_code"]="SHADOW_READY" if x["tradable_volatility_ready"] else "OBSERVATION"
            add_event(q,run,x["symbol"],1,"DISCOVERED","PASS","PROVIDER_INVENTORY",evidence={"provider":x["provider_code"]})
            contract_pass=x["data_ready"] and x["spec_ready"] and x["research_eligible"]
            add_event(q,run,x["symbol"],2,"DATA_SPEC","PASS" if contract_pass else "FAIL",
              "DATA_SPEC_READY" if contract_pass else "DATA_OR_SPEC_BLOCKED",evidence={"bars":x["bars"],"age_minutes":age,"spec_ready":x["spec_ready"]})
            add_event(q,run,x["symbol"],3,"LIQUIDITY","PASS" if contract_pass and x["liquidity_ready"] else "FAIL",
              "LIQUIDITY_READY" if x["liquidity_ready"] else "SPREAD_VOLUME_CAPACITY_BLOCKED",
              evidence={"spread_bps":x["effective_spread_bps"],"volume":x["median_volume"],"capacity_rub":x["capacity_rub"]})
            add_event(q,run,x["symbol"],4,"VOLATILITY","PASS" if x["tradable_volatility_ready"] else "FAIL",
              "TRADABLE_VOLATILITY_READY" if x["tradable_volatility_ready"] else "VOLATILITY_OR_EXECUTION_BLOCKED",
              x["tradable_volatility_score"],{"atr_pct":x["atr_pct"],"atr_percentile":x["atr_percentile"],
              "rv20":x["rv20"],"rv60":x["rv60"],"acceleration":x["volatility_acceleration"],
              "volume_zscore":x["volume_zscore"],"spread_atr_ratio":x["spread_atr_ratio"],
              "zero_volume_share":x["zero_volume_share"],"promotion_ceiling":"SHADOW"})
        eligible=[x for x in rows if x["data_ready"] and x["spec_ready"] and x["liquidity_ready"]
          and x["tradable_volatility_ready"] and x["research_eligible"]]
        selected=[]; selected_symbols=set(); quotas=policy["category_quotas"]
        def score_candidate(x):
            correlations=[abs(correlation(returns.get(x["symbol"],{}),returns.get(y["symbol"],{}))) for y in selected]
            x["max_abs_correlation"]=max(correlations,default=0.0)
            quality=min(1.0,x["bars"]/minimum)*.5+max(0,1-(x["freshness_age_minutes"] or fresh*60)/(fresh*60))*.5
            capacity=min(1.0,float(x["capacity_rub"] or 0)/max(float(policy["min_capacity_rub"])*10,1))
            diversification=1-x["max_abs_correlation"]
            weights=policy["information_weights"]
            base=(quality*float(weights["quality"])+capacity*float(weights["capacity"])+
              diversification*float(weights["diversification"])+
              x["regime_novelty_score"]/100*float(weights["regime_novelty"]))
            return .45*base+.55*x["tradable_volatility_score"]
        for code in policy["category_order"]:
            if len(selected)>=int(policy["max_selected"]): break
            pool=[x for x in eligible if x["category_code"]==code and x["symbol"] not in selected_symbols]
            slots=min(int(quotas.get(code,0)),len(pool),int(policy["max_selected"])-len(selected))
            for _ in range(slots):
                for x in pool: x["information_value_score"]=score_candidate(x)
                diversified=[x for x in pool if x["max_abs_correlation"]<=float(policy["max_abs_correlation"])]
                if not diversified: break
                choice=max(diversified,key=lambda x:(x["information_value_score"],x["bars"],x["symbol"]))
                selected.append(choice); selected_symbols.add(choice["symbol"]); pool.remove(choice)
        reserve=[]
        remaining=[x for x in eligible if x["symbol"] not in selected_symbols]
        for x in remaining: x["information_value_score"]=score_candidate(x)
        for x in sorted(remaining,key=lambda z:(-z["information_value_score"],z["symbol"]))[:int(policy["reserve_slots"])]:
            x["reserve_slot"]=True; reserve.append(x)
        ranks=defaultdict(int); counts=defaultdict(int); backfill=[]
        for x in sorted(rows,key=lambda z:(z["category_code"],-float(z.get("information_value_score") or 0),z["symbol"])):
            ranks[x["category_code"]]+=1; chosen=x["symbol"] in selected_symbols
            x.setdefault("max_abs_correlation",0.0); x.setdefault("information_value_score",0.0); x.setdefault("reserve_slot",False)
            if chosen: decision,reason,action,stage="SELECTED",["CATEGORY_QUOTA_SELECTED"],"RESEARCH_NEXT","COARSE_SEARCH"
            elif x in reserve: decision,reason,action,stage="RESERVE",["INFORMATION_RESERVE"],"KEEP_RESERVE","CATEGORY_QUOTA"
            elif x["roll_eligible"] and not x["research_eligible"]: decision,reason,action,stage="RESERVE",["NEXT_FUTURES_CONTRACT"],"MONITOR_ROLL","DATA_SPEC"
            elif x["data_ready"] and x["spec_ready"] and x["liquidity_ready"] and not x["tradable_volatility_ready"]: decision,reason,action,stage="RESERVE",["VOLATILITY_OBSERVATION_ONLY"],"KEEP_OBSERVING","VOLATILITY"
            elif x["data_ready"] and x["spec_ready"] and x["liquidity_ready"]: decision,reason,action,stage="RESERVE",["CATEGORY_QUOTA_EXCEEDED"],"KEEP_RESERVE","INFORMATION"
            elif x["spec_ready"] and x["roll_eligible"] and not x["data_ready"]: decision,reason,action,stage="BACKFILL",["INSUFFICIENT_OR_STALE_BARS"],"COLLECT_DATA","DATA_SPEC"; backfill.append(x)
            elif x["data_ready"] and x["spec_ready"]: decision,reason,action,stage="EXCLUDED",["LIQUIDITY_NOT_READY"],"COLLECT_LIQUIDITY","LIQUIDITY"
            else: decision,reason,action,stage="EXCLUDED",["SPECIFICATION_NOT_READY"],"VERIFY_SPEC","DATA_SPEC"
            counts[decision]+=1
            add_event(q,run,x["symbol"],5,"INFORMATION","PASS" if x in eligible else "FAIL","INFORMATION_SCORED",x["information_value_score"],{"correlation":x["max_abs_correlation"],"novelty":x["regime_novelty_score"]})
            add_event(q,run,x["symbol"],6,"CATEGORY_QUOTA","PASS" if chosen else "RESERVE" if x in reserve else "FAIL","CATEGORY_QUOTA_SELECTED" if chosen else "NOT_SELECTED",x["information_value_score"])
            add_event(q,run,x["symbol"],7,"COARSE_SEARCH","PASS" if chosen else "FAIL","SHADOW_RESEARCH_QUEUED" if chosen else "NOT_QUEUED",evidence={"promotion_ceiling":"SHADOW"})
            q.execute("""INSERT INTO analytics.instrument_scout_result_v1(run_id,symbol,category_code,asset_class,market_code,bars,latest_ts,
              market_score,data_ready,spec_ready,liquidity_ready,research_score,category_rank,decision_code,reason_codes,next_action_code,
              source_version,provider_code,funnel_stage_code,history_ready,freshness_age_minutes,avg_spread_bps,spread_source,median_volume,
              capacity_rub,max_abs_correlation,regime_novelty_score,information_value_score,reserve_slot,
              atr_pct,atr_percentile,rv20,rv60,volatility_acceleration,volume_zscore,directional_efficiency,
              volatility_persistence,zero_volume_share,spread_atr_ratio,tradable_volatility_score,candidate_stage_code)
              VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                     %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
              (run,x["symbol"],x["category_code"],x["asset_class"],x["market_code"],x["bars"],x["latest_ts"],x["market_score"],x["data_ready"],x["spec_ready"],x["liquidity_ready"],x["information_value_score"],ranks[x["category_code"]],decision,psycopg2.extras.Json(reason),action,SOURCE,x["provider_code"],stage,x["history_ready"],x["freshness_age_minutes"],x["effective_spread_bps"],x["spread_source"],x["median_volume"],x["capacity_rub"],x["max_abs_correlation"],x["regime_novelty_score"],x["information_value_score"],x["reserve_slot"],x["atr_pct"],x["atr_percentile"],x["rv20"],x["rv60"],x["volatility_acceleration"],x["volume_zscore"],x["directional_efficiency"],x["volatility_persistence"],x["zero_volume_share"],x["spread_atr_ratio"],x["tradable_volatility_score"],x["candidate_stage_code"]))
        additions=0; backfill.sort(key=lambda x:(x["watched"],-x["bars"],x["symbol"])); per_category=defaultdict(int)
        for x in backfill:
            if additions>=int(policy["max_new_watch_symbols_per_run"]): break
            if x["watched"] or per_category[x["category_code"]]>=1: continue
            q.execute("""INSERT INTO public.market_data_watch_universe(symbol,asset_group,timeframe,is_enabled,reason)
              VALUES(%s,%s,'M1',true,%s) ON CONFLICT(symbol) DO NOTHING RETURNING symbol""",(x["symbol"],x["category_code"],SOURCE))
            if q.fetchone(): additions+=1; per_category[x["category_code"]]+=1
        for priority,x in enumerate(selected,1):
            q.execute("""INSERT INTO analytics.instrument_scout_queue_v1(queue_id,run_id,symbol,action_code,priority,evidence)
              VALUES(%s,%s,%s,'RESEARCH_NEXT',%s,%s)""",(str(uuid.uuid4()),run,x["symbol"],priority,psycopg2.extras.Json({"source":SOURCE,"score":x["information_value_score"],"tradable_volatility_score":x["tradable_volatility_score"],"promotion_ceiling":"SHADOW"})))
        specification_pass=sum(x["data_ready"] and x["spec_ready"] and x["research_eligible"] for x in rows)
        liquidity_pass=sum(x["data_ready"] and x["spec_ready"] and x["liquidity_ready"] and x["research_eligible"] for x in rows)
        volatility_pass=len(eligible)
        q.execute("""UPDATE analytics.instrument_scout_run_v1 SET status_code='COMPLETE',discovered=%s,ready=%s,selected=%s,
          reserve=%s,backfill=%s,excluded=%s,watch_added=%s,specification_pass=%s,liquidity_pass=%s,
          volatility_pass=%s,information_ranked=%s,coarse_queued=%s,finished_at=clock_timestamp() WHERE run_id=%s""",
          (len(rows),len(eligible),len(selected),counts["RESERVE"],counts["BACKFILL"],counts["EXCLUDED"],additions,
           specification_pass,liquidity_pass,volatility_pass,len(eligible),len(selected),run))
    print(f"discovered={len(rows)} data_spec_pass={specification_pass} liquidity_pass={liquidity_pass} volatility_pass={volatility_pass}")
    print(f"information_ranked={len(eligible)} selected={len(selected)} reserve={len(reserve)} coarse_queued={len(selected)}")
    print("full_oos_share=0.10")
    print("VERDICT=AUTONOMOUS_INSTRUMENT_FUNNEL_V2_OK")
    return 0


if __name__=="__main__": raise SystemExit(main())
