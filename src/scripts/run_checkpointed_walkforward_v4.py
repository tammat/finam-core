from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import time
import uuid

import psycopg2
import psycopg2.extras

from scripts.build_edge_hypothesis_discovery_v1 import load_search_configuration
from scripts.build_strategy_execution_runner_v1 import Bar, build_trades, load_execution_context, metrics
from scripts.edge_research_universe_v1 import load_research_universe
from scripts.meta_entry_policy_v2 import apply_meta_entry_policy_v2, load_meta_entry_policy_v2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
BATCH_SECONDS = int(os.getenv("WALKFORWARD_BATCH_SECONDS", "240"))
FRESHNESS_MINUTES = int(os.getenv("EDGE_SEARCH_FRESHNESS_MINUTES", "15"))
FOLDS = 5
NAMESPACE = uuid.UUID("af257269-62c0-4dd3-b283-bf75c387cb4c")
FEATURE_VERSION = "SESSION_REGIME_FEATURE_CACHE_V1"


def _hash(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _fold_bounds(size: int, fold_no: int) -> tuple[int, int, int]:
    evaluation_start = int(size * .40)
    span = max(1, (size - evaluation_start) // FOLDS)
    start = evaluation_start + (fold_no - 1) * span
    end = size if fold_no == FOLDS else min(size, start + span)
    return evaluation_start, start, end


def _summary(trades) -> dict:
    value = metrics(trades)
    pnls = [float(t.net_pnl) for t in trades]
    gross = [float(t.gross_pnl) for t in trades]
    return {**value, "net_pnls": pnls, "gross_pnls": gross}


def _create_campaign(cur) -> dict:
    cutoff = time.strftime("%Y-%m-%dT%H:00:00+03:00")
    campaign_id = uuid.uuid5(NAMESPACE, cutoff)
    cur.execute("""INSERT INTO analytics.walkforward_campaign_v4
      (campaign_id,data_cutoff_ts,status_code,phase_code,top_share,cpu_limit)
      VALUES(%s,%s,'RUNNING','COARSE',.10,2) ON CONFLICT DO NOTHING""", (str(campaign_id), cutoff))
    markets = load_research_universe(cur, run_id=str(campaign_id), stage_code="WALKFORWARD_V4",
                                     min_bars=6000, freshness_minutes=FRESHNESS_MINUTES)
    configs = load_search_configuration(cur)
    order = 0
    for market in markets:
        for family, config in configs:
            targets = config["regime_policy"].get("target_symbols", [])
            if targets and market["symbol"] not in targets:
                continue
            algorithm_task_id = uuid.uuid5(NAMESPACE, f"{campaign_id}:{family}")
            cur.execute("""INSERT INTO analytics.walkforward_algorithm_task_v4
              (algorithm_task_id,campaign_id,algorithm_code,priority_rank)
              VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
              (str(algorithm_task_id),str(campaign_id),family,int(config.get("priority_rank",100))))
            for base in config["grid"]:
                order += 1
                parameter_hash = _hash(base)
                variant_id = uuid.uuid5(NAMESPACE, f"{algorithm_task_id}:{market['symbol']}:{market['timeframe']}:{parameter_hash}")
                cur.execute("""INSERT INTO analytics.walkforward_variant_task_v4
                  (variant_task_id,algorithm_task_id,symbol,timeframe,strategy_code,parameter_json,parameter_hash)
                  VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                  (str(variant_id),str(algorithm_task_id),market["symbol"],market["timeframe"],config["strategy_code"],
                   psycopg2.extras.Json(base),parameter_hash))
                for fold in (1,2):
                    cur.execute("""INSERT INTO analytics.walkforward_fold_checkpoint_v4(variant_task_id,fold_no)
                      VALUES(%s,%s) ON CONFLICT DO NOTHING""", (str(variant_id),fold))
    cur.execute("""UPDATE analytics.walkforward_algorithm_task_v4 a SET variants_total=(
      SELECT count(*) FROM analytics.walkforward_variant_task_v4 v WHERE v.algorithm_task_id=a.algorithm_task_id)
      WHERE campaign_id=%s""", (str(campaign_id),))
    return {"campaign_id": campaign_id, "data_cutoff_ts": cutoff}


def _load_context(cur, task: dict, cutoff) -> tuple[list[Bar], dict, dict]:
    cur.execute("""SELECT ts,close,coalesce(volume,0) volume FROM public.market_bars
      WHERE symbol=%s AND timeframe=%s AND ts<=%s AND close IS NOT NULL
        AND source NOT IN ('unknown','synthetic_futures_backfill_v1') ORDER BY ts""",
      (task["symbol"],task["timeframe"],cutoff))
    bars=[Bar(r["ts"],float(r["close"]),float(r["volume"])) for r in cur.fetchall()]
    entry=load_meta_entry_policy_v2(cur,task["symbol"],task["timeframe"],bars)
    execution=load_execution_context(cur,task["symbol"])
    cur.execute("""INSERT INTO analytics.walkforward_feature_cache_v4
      (symbol,timeframe,data_cutoff_ts,feature_version,feature_payload)
      VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
      (task["symbol"],task["timeframe"],cutoff,FEATURE_VERSION,
       psycopg2.extras.Json({"bars":len(bars),"entry_policy":entry,"execution_policy":execution})))
    return bars,entry,execution


def _execute_fold(cur, task: dict, cutoff, cache: dict) -> None:
    key=(task["symbol"],task["timeframe"])
    if key not in cache:
        cache[key]=_load_context(cur,task,cutoff)
    bars,entry,execution=cache[key]
    fold_no=int(task["fold_no"])
    evaluation_start,start,end=_fold_bounds(len(bars),max(1,fold_no))
    if fold_no == 0:
        start,end=0,evaluation_start
    params=apply_meta_entry_policy_v2(dict(task["parameter_json"]),entry)
    cost_bps=20.0 if task["symbol"].endswith("USD") else 8.0
    params.update({"transaction_cost_bps":cost_bps,"commission":statistics.median(b.close for b in bars)*cost_bps/10000,
                   "slippage":0.0,"execution_policy":execution})
    lookback=int(params["lookback"])
    start_ts,end_ts=bars[start].ts,bars[end-1].ts
    trades=[t for t in build_trades({"strategy_code":task["strategy_code"],"parameter_json":params},bars[max(0,start-lookback):end])
            if start_ts<=t.entry_ts<=end_ts]
    value=_summary(trades)
    cur.execute("""UPDATE analytics.walkforward_fold_checkpoint_v4 SET status_code='COMPLETE',
      metrics=%s,finished_at=clock_timestamp(),error_text=NULL WHERE variant_task_id=%s AND fold_no=%s""",
      (psycopg2.extras.Json(value),task["variant_task_id"],task["fold_no"]))


def _promote(cur, campaign_id) -> None:
    cur.execute("""WITH scored AS (
      SELECT v.variant_task_id,v.algorithm_task_id,
       sum(coalesce((f.metrics->>'trades')::int,0)) trades,
       avg(coalesce((f.metrics->>'expectancy')::numeric,0)) expectancy,
       avg(coalesce((f.metrics->>'profit_factor')::numeric,0)) pf,
       bool_and(coalesce((f.metrics->>'expectancy')::numeric,0)<=0) both_negative
      FROM analytics.walkforward_variant_task_v4 v
      JOIN analytics.walkforward_algorithm_task_v4 a USING(algorithm_task_id)
      JOIN analytics.walkforward_fold_checkpoint_v4 f USING(variant_task_id)
      WHERE a.campaign_id=%s AND v.phase_code='COARSE' AND f.fold_no IN (1,2)
      GROUP BY v.variant_task_id,v.algorithm_task_id
    ), ranked AS (
      SELECT s.*,percent_rank() OVER(PARTITION BY algorithm_task_id ORDER BY
        (CASE WHEN expectancy>0 THEN 1 ELSE 0 END) DESC,pf DESC,trades DESC) rank_pct
      FROM scored s
    ) UPDATE analytics.walkforward_variant_task_v4 v SET
      phase_code=CASE WHEN r.trades<20 THEN 'REJECTED' WHEN r.both_negative THEN 'REJECTED'
                      WHEN r.rank_pct<=.10 THEN 'FULL_OOS' ELSE 'REJECTED' END,
      status_code=CASE WHEN r.trades<20 OR r.both_negative OR r.rank_pct>.10 THEN 'REJECTED' ELSE 'PENDING' END,
      rejection_code=CASE WHEN r.trades<20 THEN 'EARLY_INSUFFICIENT_TRADES'
                          WHEN r.both_negative THEN 'EARLY_NEGATIVE_EXPECTANCY'
                          WHEN r.rank_pct>.10 THEN 'COARSE_NOT_TOP_10_PERCENT' END,
      coarse_score=r.pf FROM ranked r WHERE v.variant_task_id=r.variant_task_id""", (campaign_id,))
    cur.execute("""INSERT INTO analytics.walkforward_fold_checkpoint_v4(variant_task_id,fold_no)
      SELECT variant_task_id,g FROM analytics.walkforward_variant_task_v4 v
      JOIN analytics.walkforward_algorithm_task_v4 a USING(algorithm_task_id),generate_series(3,5) g
      WHERE a.campaign_id=%s AND v.phase_code='FULL_OOS' ON CONFLICT DO NOTHING""", (campaign_id,))
    cur.execute("UPDATE analytics.walkforward_campaign_v4 SET phase_code='FULL_OOS' WHERE campaign_id=%s",(campaign_id,))
    cur.execute("""INSERT INTO analytics.walkforward_fold_checkpoint_v4(variant_task_id,fold_no)
      SELECT variant_task_id,0 FROM analytics.walkforward_variant_task_v4 v
      JOIN analytics.walkforward_algorithm_task_v4 a USING(algorithm_task_id)
      WHERE a.campaign_id=%s AND v.phase_code='FULL_OOS' ON CONFLICT DO NOTHING""",(campaign_id,))


def _pf(pnls: list[float]) -> float:
    wins=sum(x for x in pnls if x>0); losses=abs(sum(x for x in pnls if x<=0))
    return wins/losses if losses else (wins if wins else 0.0)


def _finalize_results(cur,campaign_id) -> int:
    cur.execute("""SELECT v.*,a.algorithm_code,r.gate_policy,
      jsonb_object_agg(f.fold_no::text,f.metrics ORDER BY f.fold_no) fold_data
      FROM analytics.walkforward_variant_task_v4 v
      JOIN analytics.walkforward_algorithm_task_v4 a USING(algorithm_task_id)
      JOIN analytics.edge_search_algorithm_registry_v1 r ON r.algorithm_code=a.algorithm_code
      JOIN analytics.walkforward_fold_checkpoint_v4 f USING(variant_task_id)
      WHERE a.campaign_id=%s AND v.phase_code='FULL_OOS'
      GROUP BY v.variant_task_id,a.algorithm_code,r.gate_policy""",(campaign_id,))
    written=0
    for row in cur.fetchall():
      data=row["fold_data"]; gate=row["gate_policy"]["walkforward"]
      fold_rows=[]; all_net=[]; all_gross=[]; folds_passed=0
      for fold in range(1,6):
        item=data[str(fold)]; net=list(map(float,item.get("net_pnls",[]))); gross=list(map(float,item.get("gross_pnls",[])))
        passed=(len(net)>=int(gate["fold_min_trades"]) and _pf(net)>=float(gate["fold_min_profit_factor"])
                and (sum(net)/len(net) if net else 0)>float(gate["fold_min_expectancy"]))
        folds_passed+=int(passed); all_net+=net; all_gross+=gross
        fold_rows.append({"fold":fold,"trades":len(net),"profit_factor":_pf(net),
                          "expectancy":sum(net)/len(net) if net else 0,"max_drawdown":float(item.get("max_drawdown",0)),"passed":passed})
      ins=list(map(float,data["0"].get("gross_pnls",[]))); in_pass=(len(ins)>=int(gate["min_trades"]) and _pf(ins)>=float(gate["min_profit_factor"]) and (sum(ins)/len(ins) if ins else 0)>float(gate["min_expectancy"]))
      oos_gross=(len(all_gross)>=int(gate["min_trades"]) and _pf(all_gross)>=float(gate["min_profit_factor"]) and (sum(all_gross)/len(all_gross) if all_gross else 0)>float(gate["min_expectancy"]))
      after_cost=(len(all_net)>=int(gate["min_trades"]) and _pf(all_net)>=float(gate["min_profit_factor"]) and (sum(all_net)/len(all_net) if all_net else 0)>float(gate["min_expectancy"]))
      final_holdout=fold_rows[-1]["passed"]
      passed=in_pass and oos_gross and after_cost and folds_passed>=int(gate["min_folds_passed"]) and (final_holdout or not gate["final_holdout_required"])
      reason="WALKFORWARD_COST_ADJUSTED_PASS" if passed else ("INSUFFICIENT_TRADES" if len(all_net)<int(gate["min_trades"]) else "NEGATIVE_COST_ADJUSTED_EXPECTANCY" if (sum(all_net)/len(all_net) if all_net else 0)<=float(gate["min_expectancy"]) else "WALKFORWARD_FOLDS_UNSTABLE")
      funnel={"in_sample":{"passed":in_pass},"oos_gross":{"passed":oos_gross},"cost_adjusted":{"passed":after_cost},"stability":{"passed":passed,"folds_passed":folds_passed}}
      cur.execute("""INSERT INTO analytics.walkforward_edge_search_v3
       (result_id,search_run_id,strategy_family,strategy_code,symbol,timeframe,parameter_json,
        transaction_cost_bps,total_trades,net_profit_factor,net_expectancy,max_drawdown,folds_total,
        folds_passed,final_holdout_passed,fold_metrics,verdict_code,promotion_allowed,reason_code,
        source_version,in_sample_passed,oos_gross_passed,cost_adjusted_passed,stability_passed,validation_funnel)
       VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,5,%s,%s,%s,%s,false,%s,%s,%s,%s,%s,%s,%s)
       ON CONFLICT(search_run_id,strategy_code,symbol,timeframe,parameter_json) DO NOTHING""",
       (str(uuid.uuid5(NAMESPACE,f"{campaign_id}:{row['variant_task_id']}")),campaign_id,row["algorithm_code"],row["strategy_code"],row["symbol"],row["timeframe"],
        psycopg2.extras.Json(row["parameter_json"]),20 if row["symbol"].endswith("USD") else 8,len(all_net),_pf(all_net),sum(all_net)/len(all_net) if all_net else 0,
        max(float(x.get("max_drawdown",0)) for x in fold_rows),folds_passed,final_holdout,psycopg2.extras.Json(fold_rows),"OOS_PASS" if passed else "OOS_FAIL",reason,
        "CHECKPOINTED_WALKFORWARD_V4",in_pass,oos_gross,after_cost,passed,psycopg2.extras.Json(funnel)))
      written+=cur.rowcount
    return written


def _refresh(cur,campaign_id) -> dict:
    cur.execute("""SELECT c.phase_code,
      count(f.*) total,count(f.*) FILTER(WHERE f.status_code='COMPLETE') complete
      FROM analytics.walkforward_campaign_v4 c
      LEFT JOIN analytics.walkforward_algorithm_task_v4 a USING(campaign_id)
      LEFT JOIN analytics.walkforward_variant_task_v4 v USING(algorithm_task_id)
      LEFT JOIN analytics.walkforward_fold_checkpoint_v4 f USING(variant_task_id)
      WHERE c.campaign_id=%s GROUP BY c.phase_code""",(campaign_id,))
    row=dict(cur.fetchone()); total=int(row["total"]); complete=int(row["complete"])
    if row["phase_code"]=='COARSE' and total and total==complete:
        _promote(cur,campaign_id); return _refresh(cur,campaign_id)
    done=row["phase_code"]=='FULL_OOS' and total and total==complete
    if done:
        _finalize_results(cur,campaign_id)
    progress=100 if done else int(complete*100/max(1,total))
    cur.execute("""UPDATE analytics.walkforward_campaign_v4 SET tasks_total=%s,tasks_complete=%s,
      progress_pct=%s,heartbeat_at=clock_timestamp(),status_code=%s,phase_code=%s,
      finished_at=CASE WHEN %s THEN clock_timestamp() ELSE NULL END WHERE campaign_id=%s""",
      (total,complete,progress,'COMPLETE' if done else 'RUNNING','COMPLETE' if done else row['phase_code'],done,campaign_id))
    return {"total":total,"complete":complete,"progress":progress,"done":done}


def main() -> None:
    started=time.monotonic(); processed=0; cache={}
    conn=psycopg2.connect(DB); conn.autocommit=True
    try:
      with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT pg_advisory_lock(%s)",(741903128,))
        cur.execute("SELECT * FROM analytics.walkforward_campaign_v4 WHERE status_code='RUNNING' ORDER BY started_at LIMIT 1")
        campaign=cur.fetchone() or _create_campaign(cur)
        campaign_id=str(campaign["campaign_id"]); cutoff=campaign["data_cutoff_ts"]
        cur.execute("""UPDATE analytics.walkforward_fold_checkpoint_v4 f SET status_code='PENDING',error_text='RECOVERED_AFTER_STOP'
          FROM analytics.walkforward_variant_task_v4 v JOIN analytics.walkforward_algorithm_task_v4 a USING(algorithm_task_id)
          WHERE f.variant_task_id=v.variant_task_id AND a.campaign_id=%s AND f.status_code='RUNNING'""",(campaign_id,))
        while time.monotonic()-started<BATCH_SECONDS:
          cur.execute("""SELECT f.*,v.symbol,v.timeframe,v.strategy_code,v.parameter_json,a.priority_rank
            FROM analytics.walkforward_fold_checkpoint_v4 f
            JOIN analytics.walkforward_variant_task_v4 v USING(variant_task_id)
            JOIN analytics.walkforward_algorithm_task_v4 a USING(algorithm_task_id)
            WHERE a.campaign_id=%s AND f.status_code='PENDING' AND v.status_code<>'REJECTED'
            ORDER BY a.priority_rank,v.coarse_score DESC NULLS LAST,f.fold_no LIMIT 1""",(campaign_id,))
          task=cur.fetchone()
          if not task: break
          cur.execute("UPDATE analytics.walkforward_fold_checkpoint_v4 SET status_code='RUNNING',started_at=coalesce(started_at,clock_timestamp()) WHERE variant_task_id=%s AND fold_no=%s",(task["variant_task_id"],task["fold_no"]))
          try: _execute_fold(cur,task,cutoff,cache); processed+=1
          except Exception as exc:
            cur.execute("UPDATE analytics.walkforward_fold_checkpoint_v4 SET status_code='FAILED',error_text=%s,finished_at=clock_timestamp() WHERE variant_task_id=%s AND fold_no=%s",(str(exc)[:4000],task["variant_task_id"],task["fold_no"]))
        totals=_refresh(cur,campaign_id)
        cur.execute("SELECT pg_advisory_unlock(%s)",(741903128,))
    finally: conn.close()
    print(f"search_run_id={campaign_id}")
    print(f"tasks_total={totals['total']}")
    print(f"tasks_completed={totals['complete']}")
    print(f"tasks_processed={processed}")
    print(f"campaign_progress_pct={totals['progress']}")
    print(f"stage_complete={int(totals['done'])}")
    print("cpu_limit=2")
    print("promotion_allowed=0")
    print("VERDICT=CHECKPOINTED_WALKFORWARD_V4")


if __name__ == "__main__": main()
