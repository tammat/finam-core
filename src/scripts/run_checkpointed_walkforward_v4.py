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
CPU_LIMIT = min(2,max(1,int(os.getenv("OMP_NUM_THREADS","1"))))
NON_STRUCTURAL_PARAMETERS = {
    "adaptive_scenario_id","transaction_cost_bps","commission","slippage",
    "execution_policy","entry_policy_code","entry_profile_code",
}


def _hash(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _parameter_core(parameters: dict) -> dict:
    return {key:value for key,value in parameters.items() if key not in NON_STRUCTURAL_PARAMETERS}


def _are_parameter_neighbors(left: dict, right: dict) -> bool:
    left_core,right_core=_parameter_core(left),_parameter_core(right)
    keys=set(left_core)|set(right_core)
    return sum(left_core.get(key)!=right_core.get(key) for key in keys)==1


def _enqueue_remediation_variants(cur, campaign_id: str) -> int:
    """Attach DB-approved remediation candidates to the resumable coarse search."""
    cur.execute("SELECT phase_code FROM analytics.walkforward_campaign_v4 WHERE campaign_id=%s", (campaign_id,))
    campaign = cur.fetchone()
    if not campaign or campaign["phase_code"] != "COARSE":
        return 0
    cur.execute("""
      SELECT c.candidate_id,c.branch_code,c.algorithm_code,c.strategy_code,c.symbol,
             c.parameter_json,c.adaptive_scenario_id,w.timeframe,p.priority
      FROM analytics.oos_remediation_candidate_v1 c
      JOIN analytics.edge_search_adaptive_scenario_v1 s
        ON s.adaptive_scenario_id=c.adaptive_scenario_id AND s.status_code='ACTIVE'
      JOIN analytics.walkforward_edge_search_v3 w ON w.result_id=c.parent_result_id
      JOIN analytics.edge_search_resource_policy_v1 p
        ON p.branch_code=c.branch_code AND p.enabled
      WHERE c.status_code='QUEUED'
      ORDER BY p.priority,c.generated_at,c.candidate_id
    """)
    queued = [dict(row) for row in cur.fetchall()]
    inserted = 0
    for row in queued:
        algorithm_task_id = uuid.uuid5(NAMESPACE, f"{campaign_id}:{row['algorithm_code']}")
        cur.execute("""INSERT INTO analytics.walkforward_algorithm_task_v4
          (algorithm_task_id,campaign_id,algorithm_code,priority_rank,status_code)
          VALUES(%s,%s,%s,%s,'RUNNING')
          ON CONFLICT(campaign_id,algorithm_code) DO UPDATE SET
            priority_rank=least(analytics.walkforward_algorithm_task_v4.priority_rank,excluded.priority_rank),
            status_code='RUNNING',heartbeat_at=clock_timestamp()""",
          (str(algorithm_task_id),campaign_id,row["algorithm_code"],int(row["priority"])))
        parameters = dict(row["parameter_json"])
        parameters["adaptive_scenario_id"] = str(row["adaptive_scenario_id"])
        parameter_hash = _hash(parameters)
        variant_id = uuid.uuid5(NAMESPACE, f"{algorithm_task_id}:{row['symbol']}:{row['timeframe']}:{parameter_hash}")
        cur.execute("""INSERT INTO analytics.walkforward_variant_task_v4
          (variant_task_id,algorithm_task_id,symbol,timeframe,strategy_code,parameter_json,parameter_hash)
          VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
          (str(variant_id),str(algorithm_task_id),row["symbol"],row["timeframe"],row["strategy_code"],
           psycopg2.extras.Json(parameters),parameter_hash))
        inserted += cur.rowcount
        for fold in (1,2):
            cur.execute("""INSERT INTO analytics.walkforward_fold_checkpoint_v4(variant_task_id,fold_no)
              VALUES(%s,%s) ON CONFLICT DO NOTHING""", (str(variant_id),fold))
    cur.execute("""UPDATE analytics.walkforward_algorithm_task_v4 a SET variants_total=(
      SELECT count(*) FROM analytics.walkforward_variant_task_v4 v WHERE v.algorithm_task_id=a.algorithm_task_id)
      WHERE campaign_id=%s""", (campaign_id,))
    return inserted


def _reconcile_remediation_results(cur, campaign_id: str) -> None:
    """Every queued candidate ends as an audited coarse reject, OOS fail, or OOS PASS."""
    cur.execute("""
      UPDATE analytics.oos_remediation_candidate_v1 c SET
        status_code='EVALUATED_FAIL',reason_code=coalesce(v.rejection_code,'COARSE_SEARCH_REJECTED'),
        evaluated_at=clock_timestamp(),updated_at=clock_timestamp()
      FROM analytics.walkforward_variant_task_v4 v
      JOIN analytics.walkforward_algorithm_task_v4 a USING(algorithm_task_id)
      WHERE a.campaign_id=%s AND v.status_code='REJECTED'
        AND v.parameter_json->>'adaptive_scenario_id'=c.adaptive_scenario_id::text
        AND (v.parameter_json-'adaptive_scenario_id')=c.parameter_json
        AND c.status_code='QUEUED'
    """, (campaign_id,))
    cur.execute("""
      UPDATE analytics.oos_remediation_candidate_v1 c SET
        status_code=CASE WHEN w.verdict_code='OOS_PASS' THEN 'OOS_PASS' ELSE 'EVALUATED_FAIL' END,
        reason_code=CASE WHEN w.verdict_code='OOS_PASS' THEN 'UNCHANGED_GATES_PASS' ELSE w.reason_code END,
        evaluated_at=clock_timestamp(),updated_at=clock_timestamp()
      FROM analytics.walkforward_edge_search_v3 w
      WHERE w.search_run_id=%s
        AND w.parameter_json->>'adaptive_scenario_id'=c.adaptive_scenario_id::text
        AND (w.parameter_json-'adaptive_scenario_id')=c.parameter_json
        AND c.status_code='QUEUED'
    """, (campaign_id,))
    cur.execute("""
      WITH outcome AS (
        SELECT adaptive_scenario_id,bool_or(status_code='OOS_PASS') passed
        FROM analytics.oos_remediation_candidate_v1
        WHERE adaptive_scenario_id IS NOT NULL
        GROUP BY adaptive_scenario_id
        HAVING count(*) FILTER(WHERE status_code IN ('WAITING_FUTURE_DATA','QUEUED'))=0
      ) UPDATE analytics.edge_search_adaptive_scenario_v1 s SET
        status_code=CASE WHEN o.passed THEN 'EVALUATED_PASS' ELSE 'EVALUATED_FAIL' END,
        reason_code=CASE WHEN o.passed THEN 'FUTURE_DATA_PASS' ELSE 'FUTURE_DATA_NO_PASS' END,
        evaluated_at=clock_timestamp(),updated_at=clock_timestamp()
      FROM outcome o WHERE s.adaptive_scenario_id=o.adaptive_scenario_id AND s.status_code='ACTIVE'
    """)
    cur.execute("""
      WITH stats AS (
        SELECT process_id,count(*) total,
          count(*) FILTER(WHERE status_code LIKE 'PRUNED_%%' OR status_code IN ('EVALUATED_FAIL','OOS_PASS')) done,
          count(*) FILTER(WHERE status_code IN ('WAITING_FUTURE_DATA','QUEUED')) active
        FROM analytics.oos_remediation_candidate_v1 GROUP BY process_id
      ) UPDATE analytics.oos_remediation_process_v1 p SET
        status_code=CASE WHEN s.active=0 THEN 'COMPLETE' ELSE 'MONITORING' END,
        current_step_code=CASE WHEN s.active=0 THEN 'OOS_RESULTS_READY' ELSE 'WAITING_OOS_EVALUATION' END,
        progress_pct=round(100.0*s.done/greatest(1,s.total),2),
        finished_at=CASE WHEN s.active=0 THEN coalesce(p.finished_at,clock_timestamp()) ELSE NULL END,
        updated_at=clock_timestamp()
      FROM stats s WHERE p.process_id=s.process_id
    """)


def _fold_bounds(size: int, fold_no: int) -> tuple[int, int, int]:
    evaluation_start = int(size * .40)
    span = max(1, (size - evaluation_start) // FOLDS)
    start = evaluation_start + (fold_no - 1) * span
    end = size if fold_no == FOLDS else min(size, start + span)
    return evaluation_start, start, end


def _label_horizon_bars(parameters: dict) -> int:
    hold = max(1, int(parameters.get("hold", 5)))
    if str(parameters.get("exit_policy_code", "FIXED_HOLD")) == "DYNAMIC_EXIT_V1":
        return max(hold, int(parameters.get("exit_max_holding_bars", max(hold, 20))))
    return hold


def _summary(trades) -> dict:
    value = metrics(trades)
    pnls = [float(t.net_pnl) for t in trades]
    gross = [float(t.gross_pnl) for t in trades]
    daily: dict[str, float] = {}
    for trade in trades:
        day = trade.exit_ts.date().isoformat()
        daily[day] = daily.get(day, 0.0) + float(trade.net_pnl)
    quote_verified = sum(t.quote_source in {"HISTORICAL_BID_ASK","HISTORICAL_ORDER_BOOK"} for t in trades)
    depth_verified = sum(t.book_depth_verified for t in trades)
    timestamp_verified = sum(t.exchange_timestamp_verified for t in trades)
    return {
        **value,
        "net_pnls": pnls,
        "gross_pnls": gross,
        "daily_pnl": [{"date": day, "pnl": pnl} for day, pnl in sorted(daily.items())],
        "average_fill_ratio": statistics.mean(t.fill_ratio for t in trades) if trades else 0.0,
        "fallback_quote_share": 1.0 - quote_verified / len(trades) if trades else 1.0,
        "quote_coverage": quote_verified / len(trades) if trades else 0.0,
        "depth_coverage": depth_verified / len(trades) if trades else 0.0,
        "exchange_timestamp_coverage": timestamp_verified / len(trades) if trades else 0.0,
        "microstructure_coverage": min(depth_verified,timestamp_verified) / len(trades) if trades else 0.0,
        "quote_verified_trades": quote_verified,
        "depth_verified_trades": depth_verified,
        "timestamp_verified_trades": timestamp_verified,
        "session_codes": sorted({t.entry_session for t in trades if t.entry_session != "UNKNOWN"}),
        "regime_codes": sorted({t.entry_regime for t in trades if t.entry_regime != "UNKNOWN"}),
        "signal_latency_bars": min((t.latency_bars for t in trades), default=0),
        "capacity_rub": min((t.capacity_rub for t in trades), default=0.0),
        "contract_spec_coverage": (
            sum(t.contract_spec_source != "MISSING_SPEC_FALLBACK" for t in trades) / len(trades)
            if trades else 0.0
        ),
    }


def _create_campaign(cur) -> dict:
    cutoff = time.strftime("%Y-%m-%dT%H:00:00+03:00")
    campaign_id = uuid.uuid5(NAMESPACE, cutoff)

    raw_scenario_run_id = os.getenv("EDGE_SEARCH_SCENARIO_RUN_ID")
    scenario_run_id = None
    if raw_scenario_run_id:
        # Fail closed: orchestration lineage must be a valid UUID.
        scenario_run_id = str(uuid.UUID(raw_scenario_run_id))

    cur.execute("""INSERT INTO analytics.walkforward_campaign_v4
      (campaign_id,scenario_run_id,data_cutoff_ts,status_code,phase_code,top_share,cpu_limit)
      VALUES(%s,%s,%s,'RUNNING','COARSE',.10,%s) ON CONFLICT DO NOTHING""",
      (str(campaign_id), scenario_run_id, cutoff, CPU_LIMIT))

    # Детерминированный campaign_id может совпасть с ранее fail-closed
    # пустой campaign того же часового cutoff. Разрешаем повторное
    # использование только если в ней действительно нет algorithm tasks.
    cur.execute("""
      UPDATE analytics.walkforward_campaign_v4 c
      SET status_code='RUNNING',
          phase_code='COARSE',
          scenario_run_id=coalesce(c.scenario_run_id,%s::uuid),
          tasks_total=0,
          tasks_complete=0,
          progress_pct=0,
          error_text=NULL,
          finished_at=NULL,
          heartbeat_at=clock_timestamp()
      WHERE c.campaign_id=%s
        AND c.status_code='FAILED'
        AND NOT EXISTS (
          SELECT 1
          FROM analytics.walkforward_algorithm_task_v4 a
          WHERE a.campaign_id=c.campaign_id
        )
    """, (scenario_run_id, str(campaign_id)))

    try:
        markets = load_research_universe(
            cur,
            run_id=str(campaign_id),
            stage_code="WALKFORWARD_V4",
            min_bars=6000,
            freshness_minutes=FRESHNESS_MINUTES,
        )
        configs = load_search_configuration(cur)
    except Exception as exc:
        cur.execute("""
          UPDATE analytics.walkforward_campaign_v4
          SET status_code='FAILED',
              error_text=%s,
              finished_at=clock_timestamp(),
              heartbeat_at=clock_timestamp()
          WHERE campaign_id=%s
        """, (
            f"CREATE_CAMPAIGN_FAILED:{type(exc).__name__}:{str(exc)[:3500]}",
            str(campaign_id),
        ))
        raise
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
    cur.execute("""SELECT b.ts,b.close,coalesce(b.volume,0) volume,
        q.best_bid,q.best_ask,coalesce(q.bid_depth,0) bid_depth,
        coalesce(q.ask_depth,0) ask_depth,coalesce(q.bid_levels,0) bid_levels,
        coalesce(q.ask_levels,0) ask_levels,q.exchange_ts,q.observed_at quote_observed_at,
        q.source_latency_ms,coalesce(r.session_type,
          CASE
            WHEN extract(isodow FROM b.ts AT TIME ZONE 'Europe/Moscow') IN (6,7) THEN 'WEEKEND'
            WHEN extract(hour FROM b.ts AT TIME ZONE 'Europe/Moscow') < 10 THEN 'PREMARKET'
            WHEN extract(hour FROM b.ts AT TIME ZONE 'Europe/Moscow') < 14 THEN 'MOSCOW'
            WHEN extract(hour FROM b.ts AT TIME ZONE 'Europe/Moscow') < 17 THEN 'EUROPE'
            ELSE 'US_OVERLAP'
          END) session_code,
        coalesce(r.regime,'UNKNOWN') regime_code
      FROM public.market_bars b
      LEFT JOIN LATERAL (
        SELECT m.best_bid,m.best_ask,m.bid_depth,m.ask_depth,m.bid_levels,m.ask_levels,
               m.exchange_ts,m.observed_at,m.source_latency_ms
        FROM analytics.market_microstructure_snapshot_v1 m
        WHERE m.symbol=b.symbol AND m.exchange_ts>=b.ts
          AND m.exchange_ts<b.ts+interval '5 seconds'
          AND m.observed_at>=b.ts AND m.observed_at<b.ts+interval '10 seconds'
          AND m.source_latency_ms BETWEEN 0 AND 5000
        ORDER BY m.exchange_ts,m.observed_at LIMIT 1
      ) q ON true
      LEFT JOIN LATERAL (
        SELECT s.session_type,s.regime
        FROM public.analytics_regime_snapshots_v2 s
        WHERE s.symbol=b.symbol AND s.timeframe=b.timeframe AND s.ts=b.ts
        ORDER BY s.created_at DESC LIMIT 1
      ) r ON true
      WHERE b.symbol=%s AND b.timeframe=%s AND b.ts<=%s AND b.close IS NOT NULL
        AND b.source NOT IN ('unknown','synthetic_futures_backfill_v1') ORDER BY b.ts""",
      (task["symbol"],task["timeframe"],cutoff))
    bars=[Bar(
      ts=r["ts"],close=float(r["close"]),volume=float(r["volume"]),
      best_bid=float(r["best_bid"]) if r["best_bid"] is not None else None,
      best_ask=float(r["best_ask"]) if r["best_ask"] is not None else None,
      bid_depth=float(r["bid_depth"]),ask_depth=float(r["ask_depth"]),
      bid_levels=int(r["bid_levels"]),ask_levels=int(r["ask_levels"]),
      exchange_ts=r["exchange_ts"],quote_observed_at=r["quote_observed_at"],
      source_latency_ms=float(r["source_latency_ms"]) if r["source_latency_ms"] is not None else None,
      session_code=str(r["session_code"]),regime_code=str(r["regime_code"]),
    ) for r in cur.fetchall()]
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
    adaptive_scenario_id = task["parameter_json"].get("adaptive_scenario_id")
    if adaptive_scenario_id:
        cur.execute("""SELECT confirmation_after_ts FROM analytics.edge_search_adaptive_scenario_v1
          WHERE adaptive_scenario_id=%s AND status_code='ACTIVE'""", (adaptive_scenario_id,))
        scenario = cur.fetchone()
        if not scenario:
            raise RuntimeError(f"ACTIVE_REMEDIATION_SCENARIO_MISSING:{adaptive_scenario_id}")
        bars = [bar for bar in bars if bar.ts > scenario["confirmation_after_ts"]]
        entry = load_meta_entry_policy_v2(cur,task["symbol"],task["timeframe"],bars)
        if len(bars) < 60:
            raise RuntimeError(f"FUTURE_ONLY_COHORT_TOO_SHORT:{task['symbol']}:{len(bars)}")
    fold_no=int(task["fold_no"])
    evaluation_start,start,end=_fold_bounds(len(bars),max(1,fold_no))
    if fold_no == 0:
        start,end=0,evaluation_start
    params=apply_meta_entry_policy_v2(dict(task["parameter_json"]),entry)
    cost_bps=20.0 if task["symbol"].endswith("USD") else 8.0
    params.update({"transaction_cost_bps":cost_bps,"commission":statistics.median(b.close for b in bars)*cost_bps/10000,
                   "slippage":0.0,"execution_policy":execution})
    lookback=int(params["lookback"])
    embargo_bars = 0 if fold_no == 0 else _label_horizon_bars(params)
    effective_start = start + embargo_bars
    if effective_start >= end:
        raise RuntimeError(f"PURGED_FOLD_TOO_SHORT:{task['symbol']}:{fold_no}:{start}:{end}:{embargo_bars}")
    start_ts,end_ts=bars[effective_start].ts,bars[end-1].ts
    trades=[t for t in build_trades({"strategy_code":task["strategy_code"],"parameter_json":params},bars[max(0,start-lookback):end])
            if start_ts<=t.entry_ts<=end_ts and t.exit_ts<=end_ts]
    value={**_summary(trades),"start":start_ts.isoformat(),"end":end_ts.isoformat(),
           "purging_enabled":True,"embargo_bars":embargo_bars,
           "raw_fold_start":bars[start].ts.isoformat()}
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
      JOIN analytics.walkforward_algorithm_task_v4 a USING(algorithm_task_id),generate_series(3,4) g
      WHERE a.campaign_id=%s AND v.phase_code='FULL_OOS' ON CONFLICT DO NOTHING""", (campaign_id,))
    cur.execute("UPDATE analytics.walkforward_campaign_v4 SET phase_code='FULL_OOS' WHERE campaign_id=%s",(campaign_id,))
    cur.execute("""INSERT INTO analytics.walkforward_fold_checkpoint_v4(variant_task_id,fold_no)
      SELECT variant_task_id,0 FROM analytics.walkforward_variant_task_v4 v
      JOIN analytics.walkforward_algorithm_task_v4 a USING(algorithm_task_id)
      WHERE a.campaign_id=%s AND v.phase_code='FULL_OOS' ON CONFLICT DO NOTHING""",(campaign_id,))


def _select_clean_holdout(cur,campaign_id) -> None:
    """Замораживает один fingerprint до первого чтения последнего фолда."""
    cur.execute("""WITH scored AS (
      SELECT v.variant_task_id,v.algorithm_task_id,v.symbol,v.timeframe,
        sum(coalesce((f.metrics->>'trades')::int,0)) trades,
        avg(coalesce((f.metrics->>'expectancy')::numeric,0)) expectancy,
        avg(coalesce((f.metrics->>'profit_factor')::numeric,0)) pf
      FROM analytics.walkforward_variant_task_v4 v
      JOIN analytics.walkforward_algorithm_task_v4 a USING(algorithm_task_id)
      JOIN analytics.walkforward_fold_checkpoint_v4 f USING(variant_task_id)
      WHERE a.campaign_id=%s AND v.phase_code='FULL_OOS' AND f.fold_no BETWEEN 1 AND 4
      GROUP BY v.variant_task_id,v.algorithm_task_id,v.symbol,v.timeframe
    ), ranked AS (
      SELECT s.*,row_number() OVER(PARTITION BY algorithm_task_id,symbol,timeframe
        ORDER BY (expectancy>0) DESC,pf DESC,expectancy DESC,trades DESC,variant_task_id) AS selection_rank
      FROM scored s
    ) UPDATE analytics.walkforward_variant_task_v4 v SET
      phase_code=CASE WHEN r.selection_rank=1 THEN 'HOLDOUT' ELSE 'REJECTED' END,
      status_code=CASE WHEN r.selection_rank=1 THEN 'PENDING' ELSE 'REJECTED' END,
      rejection_code=CASE WHEN r.selection_rank<>1 THEN 'NOT_SELECTED_FOR_CLEAN_HOLDOUT' END
      FROM ranked r WHERE v.variant_task_id=r.variant_task_id""",(campaign_id,))
    cur.execute("""INSERT INTO analytics.walkforward_fold_checkpoint_v4(variant_task_id,fold_no)
      SELECT variant_task_id,5 FROM analytics.walkforward_variant_task_v4 v
      JOIN analytics.walkforward_algorithm_task_v4 a USING(algorithm_task_id)
      WHERE a.campaign_id=%s AND v.phase_code='HOLDOUT' ON CONFLICT DO NOTHING""",(campaign_id,))
    _record_pre_holdout_robustness(cur,campaign_id)
    cur.execute("UPDATE analytics.walkforward_campaign_v4 SET phase_code='HOLDOUT' WHERE campaign_id=%s",(campaign_id,))


def _record_pre_holdout_robustness(cur,campaign_id) -> None:
    """Use folds 1-4 only; the frozen holdout is still unread at this point."""
    cur.execute("""SELECT policy FROM analytics.edge_methodology_contract_v1
      WHERE active ORDER BY created_at DESC LIMIT 1""")
    policy_row=cur.fetchone()
    policy=dict(policy_row["policy"] if policy_row else {})
    min_pf=float(policy.get("neighbor_min_profit_factor",1.0))
    min_folds=int(policy.get("neighbor_min_folds",3))
    cur.execute("""SELECT v.variant_task_id,v.algorithm_task_id,v.symbol,v.timeframe,
      v.parameter_json,v.phase_code,r.gate_policy,
      jsonb_object_agg(f.fold_no::text,f.metrics ORDER BY f.fold_no) fold_data
      FROM analytics.walkforward_variant_task_v4 v
      JOIN analytics.walkforward_algorithm_task_v4 a USING(algorithm_task_id)
      JOIN analytics.edge_search_algorithm_registry_v1 r ON r.algorithm_code=a.algorithm_code
      JOIN analytics.walkforward_fold_checkpoint_v4 f USING(variant_task_id)
      WHERE a.campaign_id=%s AND f.fold_no BETWEEN 1 AND 4 AND f.status_code='COMPLETE'
      GROUP BY v.variant_task_id,v.algorithm_task_id,v.symbol,v.timeframe,
               v.parameter_json,v.phase_code,r.gate_policy
      HAVING count(DISTINCT f.fold_no)=4""",(campaign_id,))
    rows=[dict(row) for row in cur.fetchall()]
    summaries={}
    for row in rows:
        gate=row["gate_policy"]["walkforward"]
        all_net=[];folds_passed=0
        for fold in range(1,5):
            net=list(map(float,row["fold_data"][str(fold)].get("net_pnls",[])))
            expectancy=sum(net)/len(net) if net else 0.0
            passed=(len(net)>=int(gate["fold_min_trades"])
                    and _pf(net)>=float(gate["fold_min_profit_factor"])
                    and expectancy>float(gate["fold_min_expectancy"]))
            folds_passed+=int(passed);all_net+=net
        summaries[row["variant_task_id"]]={
            "folds_passed":folds_passed,"profit_factor":_pf(all_net),
            "expectancy":sum(all_net)/len(all_net) if all_net else 0.0,
        }
    for selected in (row for row in rows if row["phase_code"]=="HOLDOUT"):
        neighbors=[]
        for other in rows:
            if (other["variant_task_id"]==selected["variant_task_id"]
                or other["algorithm_task_id"]!=selected["algorithm_task_id"]
                or other["symbol"]!=selected["symbol"] or other["timeframe"]!=selected["timeframe"]
                or not _are_parameter_neighbors(selected["parameter_json"],other["parameter_json"])):
                continue
            summary=summaries[other["variant_task_id"]]
            if (summary["profit_factor"]>=min_pf and summary["expectancy"]>0
                and summary["folds_passed"]>=min_folds):
                neighbors.append({"variant_task_id":str(other["variant_task_id"]),**summary})
        evidence={
            "selection_folds":[1,2,3,4],"holdout_fold_unread":True,
            "robust_neighbors":len(neighbors),"supportive_neighbors":neighbors,
            "neighbor_min_profit_factor":min_pf,"neighbor_min_folds":min_folds,
        }
        cur.execute("""UPDATE analytics.walkforward_variant_task_v4
          SET pre_holdout_evidence=%s WHERE variant_task_id=%s""",
          (psycopg2.extras.Json(evidence),selected["variant_task_id"]))


def _pf(pnls: list[float]) -> float:
    wins=sum(x for x in pnls if x>0); losses=abs(sum(x for x in pnls if x<=0))
    return wins/losses if losses else (wins if wins else 0.0)


def _one_sided_sign_p_value(pnls: list[float]) -> float:
    """Exact one-sided sign test; FDR correction remains a contract gate."""
    nonzero = [value for value in pnls if value != 0]
    n = len(nonzero)
    wins = sum(value > 0 for value in nonzero)
    if not n:
        return 1.0
    return min(1.0, sum(math.comb(n, k) for k in range(wins, n + 1)) / (2 ** n))


def _finalize_results(cur,campaign_id) -> int:
    cur.execute("""SELECT v.*,a.algorithm_code,r.gate_policy,
      jsonb_object_agg(f.fold_no::text,f.metrics ORDER BY f.fold_no) fold_data
      FROM analytics.walkforward_variant_task_v4 v
      JOIN analytics.walkforward_algorithm_task_v4 a USING(algorithm_task_id)
      JOIN analytics.edge_search_algorithm_registry_v1 r ON r.algorithm_code=a.algorithm_code
      JOIN analytics.walkforward_fold_checkpoint_v4 f USING(variant_task_id)
      WHERE a.campaign_id=%s AND v.phase_code='HOLDOUT'
      GROUP BY v.variant_task_id,a.algorithm_code,r.gate_policy""",(campaign_id,))
    written=0
    for row in cur.fetchall():
      data=row["fold_data"]; gate=row["gate_policy"]["walkforward"]
      fold_rows=[]; all_net=[]; all_gross=[]; folds_passed=0
      all_sessions=set();all_regimes=set();all_days=set()
      quote_verified=depth_verified=timestamp_verified=execution_trades=0
      for fold in range(1,6):
        item=data[str(fold)]; net=list(map(float,item.get("net_pnls",[]))); gross=list(map(float,item.get("gross_pnls",[])))
        passed=(len(net)>=int(gate["fold_min_trades"]) and _pf(net)>=float(gate["fold_min_profit_factor"])
                and (sum(net)/len(net) if net else 0)>float(gate["fold_min_expectancy"]))
        folds_passed+=int(passed); all_net+=net; all_gross+=gross
        all_sessions.update(item.get("session_codes",[]));all_regimes.update(item.get("regime_codes",[]))
        all_days.update(day["date"] for day in item.get("daily_pnl",[]) if day.get("date"))
        quote_verified+=int(item.get("quote_verified_trades",0))
        depth_verified+=int(item.get("depth_verified_trades",0))
        timestamp_verified+=int(item.get("timestamp_verified_trades",0))
        execution_trades+=len(net)
        fold_rows.append({"fold":fold,"trades":len(net),"profit_factor":_pf(net),
                          "expectancy":sum(net)/len(net) if net else 0,
                          "max_drawdown":float(item.get("max_drawdown",0)),
                          "start":item.get("start"),"end":item.get("end"),"passed":passed})
      ins=list(map(float,data["0"].get("gross_pnls",[]))); in_pass=(len(ins)>=int(gate["min_trades"]) and _pf(ins)>=float(gate["min_profit_factor"]) and (sum(ins)/len(ins) if ins else 0)>float(gate["min_expectancy"]))
      oos_gross=(len(all_gross)>=int(gate["min_trades"]) and _pf(all_gross)>=float(gate["min_profit_factor"]) and (sum(all_gross)/len(all_gross) if all_gross else 0)>float(gate["min_expectancy"]))
      after_cost=(len(all_net)>=int(gate["min_trades"]) and _pf(all_net)>=float(gate["min_profit_factor"]) and (sum(all_net)/len(all_net) if all_net else 0)>float(gate["min_expectancy"]))
      final_holdout=fold_rows[-1]["passed"]
      passed=in_pass and oos_gross and after_cost and folds_passed>=int(gate["min_folds_passed"]) and (final_holdout or not gate["final_holdout_required"])
      reason="WALKFORWARD_COST_ADJUSTED_PASS" if passed else ("INSUFFICIENT_TRADES" if len(all_net)<int(gate["min_trades"]) else "NEGATIVE_COST_ADJUSTED_EXPECTANCY" if (sum(all_net)/len(all_net) if all_net else 0)<=float(gate["min_expectancy"]) else "WALKFORWARD_FOLDS_UNSTABLE")
      gross_pf=_pf(all_gross); gross_expectancy=sum(all_gross)/len(all_gross) if all_gross else 0
      net_pf=_pf(all_net); net_expectancy=sum(all_net)/len(all_net) if all_net else 0
      stressed_net=[gross-1.5*(gross-net) for gross,net in zip(all_gross,all_net)]
      holdout_metrics=data["5"]
      pre_holdout=dict(row.get("pre_holdout_evidence") or {})
      methodology_evidence={
        "one_sided_p_value":_one_sided_sign_p_value(all_net),
        "stressed_profit_factor":_pf(stressed_net),
        "stressed_expectancy":sum(stressed_net)/len(stressed_net) if stressed_net else 0.0,
        "average_fill_ratio":float(holdout_metrics.get("average_fill_ratio",0)),
        "fallback_quote_share":float(holdout_metrics.get("fallback_quote_share",1)),
        "quote_coverage":quote_verified/execution_trades if execution_trades else 0.0,
        "depth_coverage":depth_verified/execution_trades if execution_trades else 0.0,
        "exchange_timestamp_coverage":timestamp_verified/execution_trades if execution_trades else 0.0,
        "microstructure_coverage":min(depth_verified,timestamp_verified)/execution_trades if execution_trades else 0.0,
        "signal_latency_bars":int(holdout_metrics.get("signal_latency_bars",0)),
        "capacity_rub":float(holdout_metrics.get("capacity_rub",0)),
        "contract_spec_coverage":float(holdout_metrics.get("contract_spec_coverage",0)),
        "holdout_access_code":"OPENED",
        "daily_pnl":holdout_metrics.get("daily_pnl",[]),
        "independent_trade_days":len(all_days),
        "session_codes":sorted(all_sessions),"independent_sessions":len(all_sessions),
        "regime_codes":sorted(all_regimes),"independent_regimes":len(all_regimes),
        "pre_holdout_robust_neighbors":int(pre_holdout.get("robust_neighbors",0)),
        "pre_holdout_robustness":pre_holdout,
        "pnl_stdev":statistics.pstdev(all_net) if len(all_net)>1 else 0.0,
        "future_only":bool(row["parameter_json"].get("adaptive_scenario_id")),
        "fold_overlap_forbidden":True,
      }
      funnel={
        "in_sample":{"passed":in_pass},
        "oos_gross":{"trades":len(all_gross),"profit_factor":gross_pf,
                     "expectancy":gross_expectancy,"passed":oos_gross},
        "cost_adjusted":{"trades":len(all_net),"profit_factor":net_pf,
                         "expectancy":net_expectancy,"passed":after_cost},
        "cost_waterfall":{"transaction_cost_bps":20 if row["symbol"].endswith("USD") else 8,
                          "gross_expectancy":gross_expectancy,"net_expectancy":net_expectancy,
                          "expectancy_lost":gross_expectancy-net_expectancy,
                          "diagnostic_only":True,"promotion_allowed":False,
                          "runtime_allowed":False},
        "stability":{"passed":passed,"folds_passed":folds_passed}}
      cur.execute("""INSERT INTO analytics.walkforward_edge_search_v3
       (result_id,search_run_id,strategy_family,strategy_code,symbol,timeframe,parameter_json,
        transaction_cost_bps,total_trades,net_profit_factor,net_expectancy,max_drawdown,folds_total,
        folds_passed,final_holdout_passed,fold_metrics,verdict_code,promotion_allowed,reason_code,
        source_version,in_sample_passed,oos_gross_passed,cost_adjusted_passed,stability_passed,
        validation_funnel,methodology_evidence)
       VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,5,%s,%s,%s,%s,false,%s,%s,%s,%s,%s,%s,%s,%s)
       ON CONFLICT(search_run_id,strategy_code,symbol,timeframe,parameter_json) DO NOTHING""",
       (str(uuid.uuid5(NAMESPACE,f"{campaign_id}:{row['variant_task_id']}")),campaign_id,row["algorithm_code"],row["strategy_code"],row["symbol"],row["timeframe"],
        psycopg2.extras.Json(row["parameter_json"]),20 if row["symbol"].endswith("USD") else 8,len(all_net),_pf(all_net),sum(all_net)/len(all_net) if all_net else 0,
        max(float(x.get("max_drawdown",0)) for x in fold_rows),folds_passed,final_holdout,psycopg2.extras.Json(fold_rows),"OOS_PASS" if passed else "OOS_FAIL",reason,
        "CHECKPOINTED_WALKFORWARD_V4",in_pass,oos_gross,after_cost,passed,
        psycopg2.extras.Json(funnel),psycopg2.extras.Json(methodology_evidence)))
      written+=cur.rowcount
    return written


def _refresh(cur,campaign_id) -> dict:
    cur.execute("""UPDATE analytics.walkforward_variant_task_v4 v SET status_code='COMPLETE'
      WHERE v.phase_code IN ('FULL_OOS','HOLDOUT') AND v.status_code<>'COMPLETE'
        AND NOT EXISTS(SELECT 1 FROM analytics.walkforward_fold_checkpoint_v4 f
          WHERE f.variant_task_id=v.variant_task_id AND f.status_code<>'COMPLETE')""")
    cur.execute("""UPDATE analytics.walkforward_algorithm_task_v4 a SET
      variants_complete=(SELECT count(*) FROM analytics.walkforward_variant_task_v4 v
        WHERE v.algorithm_task_id=a.algorithm_task_id AND v.status_code IN ('COMPLETE','REJECTED')),
      status_code=CASE WHEN NOT EXISTS(SELECT 1 FROM analytics.walkforward_variant_task_v4 v
        WHERE v.algorithm_task_id=a.algorithm_task_id AND v.status_code NOT IN ('COMPLETE','REJECTED'))
        THEN 'COMPLETE' ELSE 'RUNNING' END,heartbeat_at=clock_timestamp()
      WHERE a.campaign_id=%s""",(campaign_id,))
    cur.execute("""SELECT c.phase_code,
      count(f.*) total,count(f.*) FILTER(WHERE f.status_code='COMPLETE') complete
      FROM analytics.walkforward_campaign_v4 c
      LEFT JOIN analytics.walkforward_algorithm_task_v4 a USING(campaign_id)
      LEFT JOIN analytics.walkforward_variant_task_v4 v USING(algorithm_task_id)
      LEFT JOIN analytics.walkforward_fold_checkpoint_v4 f USING(variant_task_id)
      WHERE c.campaign_id=%s GROUP BY c.phase_code""",(campaign_id,))
    row=dict(cur.fetchone()); total=int(row["total"]); complete=int(row["complete"])
    if row["phase_code"] == 'COMPLETE':
        cur.execute("""UPDATE analytics.walkforward_campaign_v4 SET
          status_code='COMPLETE',progress_pct=100,tasks_total=%s,tasks_complete=%s,
          heartbeat_at=clock_timestamp(),finished_at=coalesce(finished_at,clock_timestamp())
          WHERE campaign_id=%s""",(total,complete,campaign_id))
        return {"total":total,"complete":complete,"progress":100,"done":True}
    if row["phase_code"]=='COARSE' and total and total==complete:
        _promote(cur,campaign_id); return _refresh(cur,campaign_id)
    if row["phase_code"]=='FULL_OOS' and total and total==complete:
        _select_clean_holdout(cur,campaign_id); return _refresh(cur,campaign_id)
    done=row["phase_code"]=='HOLDOUT' and total and total==complete
    if done:
        _finalize_results(cur,campaign_id)
        _reconcile_remediation_results(cur,campaign_id)
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
        cur.execute("""UPDATE analytics.walkforward_campaign_v4 SET
          status_code='COMPLETE',progress_pct=100,
          finished_at=coalesce(finished_at,clock_timestamp()),heartbeat_at=clock_timestamp()
          WHERE phase_code='COMPLETE' AND status_code<>'COMPLETE'""")
        cur.execute("""
          UPDATE analytics.walkforward_campaign_v4 c
          SET status_code='FAILED',
              error_text='EMPTY_RUNNING_CAMPAIGN_NO_ALGORITHM_TASKS',
              finished_at=clock_timestamp(),
              heartbeat_at=clock_timestamp()
          WHERE c.status_code='RUNNING'
            AND c.phase_code<>'COMPLETE'
            AND NOT EXISTS (
              SELECT 1
              FROM analytics.walkforward_algorithm_task_v4 a
              WHERE a.campaign_id=c.campaign_id
            )
        """)

        cur.execute("""SELECT * FROM analytics.walkforward_campaign_v4
          WHERE status_code='RUNNING' AND phase_code<>'COMPLETE'
          ORDER BY started_at LIMIT 1""")
        campaign=cur.fetchone() or _create_campaign(cur)
        campaign_id=str(campaign["campaign_id"]); cutoff=campaign["data_cutoff_ts"]
        remediation_inserted=_enqueue_remediation_variants(cur,campaign_id)
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
          cur.execute("UPDATE analytics.walkforward_fold_checkpoint_v4 SET status_code='RUNNING',attempts=attempts+1,started_at=coalesce(started_at,clock_timestamp()) WHERE variant_task_id=%s AND fold_no=%s",(task["variant_task_id"],task["fold_no"]))
          try: _execute_fold(cur,task,cutoff,cache); processed+=1
          except Exception as exc:
            terminal=int(task.get("attempts",0))+1>=3
            cur.execute("""UPDATE analytics.walkforward_fold_checkpoint_v4 SET status_code=%s,error_text=%s,
              finished_at=CASE WHEN %s THEN clock_timestamp() ELSE NULL END
              WHERE variant_task_id=%s AND fold_no=%s""",
              ('FAILED' if terminal else 'PENDING',str(exc)[:4000],terminal,task["variant_task_id"],task["fold_no"]))
            if terminal:
              cur.execute("""UPDATE analytics.walkforward_campaign_v4 SET status_code='FAILED',
                error_text=%s,finished_at=clock_timestamp() WHERE campaign_id=%s""",(str(exc)[:4000],campaign_id))
              break
        totals=_refresh(cur,campaign_id)
        cur.execute("SELECT pg_advisory_unlock(%s)",(741903128,))
    finally: conn.close()
    print(f"search_run_id={campaign_id}")
    print(f"tasks_total={totals['total']}")
    print(f"tasks_completed={totals['complete']}")
    print(f"tasks_processed={processed}")
    print(f"remediation_variants_inserted={remediation_inserted}")
    print(f"campaign_progress_pct={totals['progress']}")
    print(f"stage_complete={int(totals['done'])}")
    print(f"cpu_limit={CPU_LIMIT}")
    print("promotion_allowed=0")
    print("VERDICT=CHECKPOINTED_WALKFORWARD_V4")


if __name__ == "__main__": main()
