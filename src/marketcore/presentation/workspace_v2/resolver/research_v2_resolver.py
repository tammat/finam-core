from __future__ import annotations
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
import psycopg2
import psycopg2.extras
from marketcore.presentation.workspace_v2.domain.research_snapshot_v2 import EdgeSearchRunAuditV1,FuturesRollItemV1,InstrumentScoutItemV1,MethodologyGateFailureV1,ResearchAlgorithmResultV2,ResearchSnapshotV2,ResearchUniverseItemV1,StrategyDegradationV1

def _utc(value):
    if value is None: return None
    return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value).astimezone(timezone.utc)

def _count_symbols(value):
    return len([item for item in str(value or "").split(",") if item.strip()])

def _next_scout_run(now, schedule, last_run):
    zone=ZoneInfo(str(schedule.get("timezone_code") or "Europe/Moscow"))
    local=now.astimezone(zone); start=schedule.get("window_start") or time(1)
    candidate=datetime.combine(local.date(),start,tzinfo=zone)
    if local>=candidate or (last_run and last_run.astimezone(zone).date()>=local.date()): candidate+=timedelta(days=1)
    weekdays=set(schedule.get("weekdays") or range(7))
    while candidate.weekday() not in weekdays: candidate+=timedelta(days=1)
    return candidate.astimezone(timezone.utc)

class ResearchV2Resolver:
    def resolve(self, *, generated_at=None):
        now=_utc(generated_at) or datetime.now(timezone.utc)
        with psycopg2.connect("postgresql:///finam_core") as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT status,active_symbols,failed_symbols,last_cycle_at FROM public.research_runtime_state ORDER BY updated_at DESC LIMIT 1")
                runtime=cursor.fetchone() or {}
                cursor.execute("SELECT research_candidates,oos_pass,paper_ready,refreshed_at FROM marketcore_ui.research_summary_v1 WHERE id=1")
                summary=cursor.fetchone() or {}
                cursor.execute("SELECT count(*) total,count(*) FILTER (WHERE status_code NOT IN ('DONE','FAILED')) pending,count(*) FILTER (WHERE status_code='FAILED') failed,max(updated_at) updated_at FROM analytics.research_queue_v1")
                queue=cursor.fetchone()
                cursor.execute("SELECT count(*) total,count(*) FILTER (WHERE verdict_code='OOS_PASS') passed,max(updated_at) updated_at FROM analytics.edge_oos_result_v1")
                oos=cursor.fetchone()
                cursor.execute("SELECT status_code status,current_step,progress_pct,markets_evaluated,combinations_evaluated,oos_pass,finished_at FROM analytics.edge_search_cycle_status_v1 ORDER BY started_at DESC LIMIT 1")
                edge_search=cursor.fetchone() or {}
                cursor.execute("""SELECT item_count,total_parameter_variants
                    FROM analytics.edge_next_research_plan_v1
                    ORDER BY created_at DESC LIMIT 1""")
                next_plan=cursor.fetchone() or {}
                cursor.execute("""SELECT count(*) AS active
                    FROM marketcore_action.command_request_v2
                    WHERE request_kind='EDGE_SEARCH_RUN' AND status IN ('PENDING','RUNNING')""")
                edge_auto_queue=cursor.fetchone() or {}
                cursor.execute("""SELECT status_code
                    FROM analytics.edge_search_auto_schedule_state_v1
                    WHERE scheduler_code='EDGE_SEARCH_AUTO'""")
                edge_auto_status=cursor.fetchone() or {}
                cursor.execute("""SELECT run_id,status_code,discovered,selected,backfill,watch_added,started_at
                    FROM analytics.instrument_scout_run_v1 ORDER BY started_at DESC LIMIT 1""")
                scout=cursor.fetchone() or {}
                cursor.execute("""SELECT s.symbol,s.category_code,s.bars,s.research_score,s.decision_code,
                           coalesce(s.reason_codes->>0,'NO_REASON') reason_code,s.next_action_code,
                           a.process_id,coalesce(a.status_code,'NOT_REQUESTED') action_status,
                           coalesce(a.progress_pct,0) action_progress,coalesce(a.current_step_code,'AVAILABLE') action_step
                    FROM analytics.instrument_scout_result_v1 s
                    LEFT JOIN LATERAL (
                      SELECT q.process_id,p.status_code,p.progress_pct,p.current_step_code
                      FROM marketcore_action.command_request_v2 q
                      LEFT JOIN marketcore_action.research_process_v1 p ON p.process_id=q.process_id
                      WHERE q.request_kind LIKE 'RESEARCH_UNIVERSE_%%'
                        AND split_part(coalesce(q.target_id,''),'|',1)=s.symbol
                      ORDER BY q.requested_at DESC LIMIT 1) a ON true
                    WHERE s.run_id=%s
                    ORDER BY CASE s.decision_code WHEN 'SELECTED' THEN 1 WHEN 'RESERVE' THEN 2
                              WHEN 'BACKFILL' THEN 3 ELSE 4 END,s.research_score DESC,s.symbol
                    LIMIT 80""",(scout.get("run_id"),))
                scout_items=tuple(InstrumentScoutItemV1(
                    str(row["symbol"]),str(row["category_code"]),int(row["bars"] or 0),
                    float(row["research_score"] or 0),str(row["decision_code"]),
                    str(row["reason_code"]),str(row["next_action_code"]),
                    str(row["process_id"]) if row["process_id"] else None,str(row["action_status"]),
                    float(row["action_progress"]),str(row["action_step"])) for row in cursor.fetchall()) if scout else ()
                cursor.execute("""SELECT s.*,r.started_at,r.finished_at,r.status_code run_status
                    FROM analytics.system_job_schedule_v1 s
                    LEFT JOIN LATERAL (SELECT started_at,finished_at,status_code FROM analytics.system_job_run_v1
                      WHERE job_code=s.job_code ORDER BY started_at DESC LIMIT 1) r ON true
                    WHERE s.job_code='INSTRUMENT_SCOUT_DAILY'""")
                scout_schedule=cursor.fetchone() or {}
                scout_last=_utc(scout_schedule.get("started_at") or scout.get("started_at"))
                scout_next=_next_scout_run(now,scout_schedule,scout_last) if scout_schedule else None
                cursor.execute("""WITH latest AS (
                    SELECT scenario_run_id FROM analytics.edge_methodology_evaluation_v1
                    ORDER BY created_at DESC LIMIT 1)
                    SELECT count(*) AS evaluated,count(*) FILTER(WHERE verdict_code='PASS') AS passed
                    FROM analytics.edge_methodology_evaluation_v1
                    WHERE scenario_run_id=(SELECT scenario_run_id FROM latest)""")
                methodology=cursor.fetchone() or {}
                cursor.execute("""WITH latest AS (
                    SELECT scenario_run_id FROM analytics.edge_methodology_evaluation_v1
                    ORDER BY created_at DESC LIMIT 1)
                    SELECT count(*) AS total,
                      count(*) FILTER(WHERE NOT statistical_pass) AS statistical,
                      count(*) FILTER(WHERE NOT robustness_pass) AS robustness,
                      count(*) FILTER(WHERE NOT holdout_pass) AS holdout,
                      count(*) FILTER(WHERE NOT execution_pass) AS execution,
                      count(*) FILTER(WHERE NOT capacity_pass) AS capacity,
                      count(*) FILTER(WHERE NOT portfolio_pass) AS portfolio
                    FROM analytics.edge_methodology_evaluation_v1
                    WHERE scenario_run_id=(SELECT scenario_run_id FROM latest)""")
                gate_counts=cursor.fetchone() or {}
                gate_total=int(gate_counts.get("total") or 0)
                methodology_failures=tuple(MethodologyGateFailureV1(
                    code,gate_total,int(gate_counts.get(code) or 0),
                    gate_total-int(gate_counts.get(code) or 0),
                    round(100.0*int(gate_counts.get(code) or 0)/gate_total,2) if gate_total else 0.0,
                    "NO_DATA" if not gate_total else ("PASS" if not int(gate_counts.get(code) or 0) else "FAIL")
                ) for code in ("statistical","robustness","holdout","execution","capacity","portfolio"))
                cursor.execute("""WITH quote_health AS (
                      SELECT count(*) FILTER(WHERE health_status='FRESH' AND signal_allowed) quote_symbols,
                             bool_or(health_status='FRESH' AND signal_allowed) quote_ready
                      FROM analytics.microstructure_health_v1)
                    SELECT q.quote_symbols,s.ready_count spec_count,
                           CASE WHEN q.quote_ready THEN 'READY' ELSE 'STALE' END quote_status,
                           s.health_code spec_status
                    FROM quote_health q CROSS JOIN analytics.contract_spec_sync_health_v1 s""")
                execution=cursor.fetchone() or {}
                cursor.execute("""WITH latest AS (
                    SELECT scenario_run_id FROM analytics.research_global_experiment_v1
                    ORDER BY created_at DESC LIMIT 1)
                  SELECT (SELECT count(*) FROM analytics.research_global_experiment_v1) global_trials,
                    count(*) FILTER(WHERE verdict_code='PASS') global_pass,
                    count(*) FILTER(WHERE asset_class='EQUITY') equity_experiments,
                    count(*) FILTER(WHERE asset_class='FUTURES') futures_experiments
                  FROM analytics.research_global_experiment_v1
                  WHERE scenario_run_id=(SELECT scenario_run_id FROM latest)""")
                governance=cursor.fetchone() or {}
                cursor.execute("""WITH latest AS (
                    SELECT scenario_run_id FROM analytics.pnl_unit_audit_v1
                    ORDER BY audited_at DESC LIMIT 1)
                  SELECT count(*) FILTER(WHERE status_code='READY') pnl_ready,
                         count(*) FILTER(WHERE status_code='BLOCKED') pnl_blocked
                  FROM analytics.pnl_unit_audit_v1
                  WHERE scenario_run_id=(SELECT scenario_run_id FROM latest)""")
                pnl_units=cursor.fetchone() or {}
                cursor.execute("""WITH latest AS (
                    SELECT search_run_id FROM analytics.research_global_experiment_v1
                    ORDER BY created_at DESC LIMIT 1)
                  SELECT count(DISTINCT (symbol,timeframe,holdout_start,holdout_end)) opened,
                    (SELECT count(*) FROM analytics.walkforward_edge_search_v3
                     WHERE search_run_id=(SELECT search_run_id FROM latest)
                       AND methodology_evidence->>'holdout_access_code'='REUSED_BLOCKED') reused
                  FROM analytics.research_holdout_snapshot_v1
                  WHERE owner_search_run_id=(SELECT search_run_id FROM latest)""")
                holdout=cursor.fetchone() or {}
                cursor.execute("""WITH latest AS (
                    SELECT scenario_run_id FROM analytics.edge_portfolio_selection_v1
                    ORDER BY created_at DESC LIMIT 1)
                  SELECT count(*) FILTER(WHERE selected) selected
                  FROM analytics.edge_portfolio_selection_v1
                  WHERE scenario_run_id=(SELECT scenario_run_id FROM latest)""")
                portfolio_selection=cursor.fetchone() or {}
                cursor.execute("""SELECT total_variants AS total,in_sample_pass AS in_sample,
                    oos_pass AS oos,after_costs_pass AS after_costs,stable_pass AS stable,
                    bottleneck_stage,lost_variants,recommendation_code
                  FROM analytics.edge_validation_funnel_analysis_v1
                  ORDER BY created_at DESC LIMIT 1""")
                validation_funnel=cursor.fetchone() or {}
                cursor.execute("""WITH latest AS (
                    SELECT search_run_id FROM analytics.edge_strategy_degradation_v1
                    ORDER BY created_at DESC LIMIT 1)
                  SELECT strategy_code,symbol,100*oos_retention AS oos_retention_pct,
                    100*cost_retention AS cost_retention_pct,
                    100*stability_retention AS stability_retention_pct,
                    consecutive_degraded_cycles,degradation_code,promotion_blocked,
                    research_quarantine_required
                  FROM analytics.edge_strategy_degradation_v1
                  WHERE search_run_id=(SELECT search_run_id FROM latest)
                  ORDER BY research_quarantine_required DESC,consecutive_degraded_cycles DESC,
                    strategy_code,symbol""")
                strategy_degradation=tuple(StrategyDegradationV1(
                    str(row["strategy_code"]),str(row["symbol"]),
                    float(row["oos_retention_pct"]),float(row["cost_retention_pct"]),
                    float(row["stability_retention_pct"]),int(row["consecutive_degraded_cycles"]),
                    str(row["degradation_code"]),bool(row["promotion_blocked"]),
                    bool(row["research_quarantine_required"])) for row in cursor.fetchall())
                cursor.execute("""WITH latest AS (
                    SELECT DISTINCT ON(root_symbol) root_symbol,current_symbol,next_symbol,
                      selected_symbol,days_to_expiry,current_median_volume,next_median_volume,
                      decision_code,created_at
                    FROM analytics.futures_roll_decision_v1 ORDER BY root_symbol,created_at DESC)
                  SELECT l.*,p.policy,
                    coalesce(m.source,'LEVERAGE_CAP_FALLBACK') margin_source
                  FROM latest l CROSS JOIN analytics.futures_autonomy_policy_v1 p
                  LEFT JOIN public.margin_requirements m ON m.symbol=l.selected_symbol AND m.active
                  WHERE p.active ORDER BY l.root_symbol""")
                futures_roll_items=[]
                for row in cursor.fetchall():
                    current_volume=float(row["current_median_volume"] or 0)
                    next_volume=float(row["next_median_volume"] or 0)
                    progress=round(min(100.0,100.0*next_volume/current_volume),1) if current_volume else 0.0
                    status=("ROLLED" if row["selected_symbol"]!=row["current_symbol"] else
                            "WATCH" if int(row["days_to_expiry"])<=7 else "READY")
                    policy=row["policy"]
                    futures_roll_items.append(FuturesRollItemV1(
                        str(row["root_symbol"]),str(row["current_symbol"] or ""),str(row["next_symbol"] or ""),
                        str(row["selected_symbol"]),int(row["days_to_expiry"]),current_volume,next_volume,
                        progress,str(row["decision_code"]),status,float(policy["max_gross_leverage"]),
                        100.0*float(policy["max_position_share"]),str(row["margin_source"])))
                futures_roll_items=tuple(futures_roll_items)
                cursor.execute("""WITH latest AS (
                    SELECT run_id FROM analytics.edge_research_universe_snapshot_v1
                    WHERE stage_code='WALKFORWARD' ORDER BY created_at DESC LIMIT 1)
                    SELECT u.symbol,u.category_code,u.bars,u.category_rank,u.selected,u.reason_code,
                           a.process_id,coalesce(a.status_code,'NOT_REQUESTED') action_status,
                           coalesce(a.progress_pct,0) action_progress,
                           coalesce(a.current_step_code,'AVAILABLE') action_step
                    FROM analytics.edge_research_universe_snapshot_v1 u
                    LEFT JOIN LATERAL (
                      SELECT q.process_id,p.status_code,p.progress_pct,p.current_step_code
                      FROM marketcore_action.command_request_v2 q
                      LEFT JOIN marketcore_action.research_process_v1 p ON p.process_id=q.process_id
                      WHERE q.request_kind LIKE 'RESEARCH_UNIVERSE_%%'
                        AND split_part(coalesce(q.target_id,''),'|',1)=u.symbol
                      ORDER BY q.requested_at DESC LIMIT 1
                    ) a ON true
                    WHERE stage_code='WALKFORWARD' AND run_id=(SELECT run_id FROM latest)
                    ORDER BY selected DESC,category_code,category_rank,symbol""")
                universe_items=tuple(ResearchUniverseItemV1(str(row["symbol"]),str(row["category_code"]),
                    int(row["bars"]),int(row["category_rank"]),bool(row["selected"]),str(row["reason_code"]),
                    str(row["process_id"]) if row["process_id"] else None,str(row["action_status"]),
                    float(row["action_progress"]),str(row["action_step"]))
                    for row in cursor.fetchall())
                cursor.execute("""
                    WITH latest AS (
                        SELECT search_run_id FROM analytics.walkforward_edge_search_v3
                        WHERE source_version='WALKFORWARD_EDGE_SEARCH_V4_TRUSTED_BARS'
                        ORDER BY created_at DESC LIMIT 1
                    )
                    SELECT strategy_family,count(DISTINCT symbol) markets,count(*) variants,
                           max(folds_passed) best_folds,max(folds_total) folds_total,
                           coalesce(max(net_profit_factor) FILTER (WHERE total_trades>=80),0) best_profit_factor,
                           count(*) FILTER (WHERE verdict_code='OOS_PASS') passes,
                           mode() WITHIN GROUP (ORDER BY CASE
                               WHEN total_trades<80 THEN 'INSUFFICIENT_TRADES'
                               WHEN net_expectancy<=0 THEN 'NEGATIVE_COST_ADJUSTED_EXPECTANCY'
                               WHEN net_profit_factor<1.15 THEN 'PROFIT_FACTOR_BELOW_GATE'
                               WHEN folds_passed<4 THEN 'WALKFORWARD_FOLDS_UNSTABLE'
                               WHEN NOT final_holdout_passed THEN 'FINAL_HOLDOUT_FAILED'
                               ELSE reason_code END) fail_reason
                    FROM analytics.walkforward_edge_search_v3
                    WHERE search_run_id=(SELECT search_run_id FROM latest)
                    GROUP BY strategy_family
                    ORDER BY CASE strategy_family WHEN 'RSI' THEN 1 WHEN 'VWAP' THEN 2 WHEN 'BOLLINGER' THEN 3 WHEN 'MOMENTUM' THEN 4 ELSE 5 END
                """)
                algorithms=tuple(ResearchAlgorithmResultV2(str(row["strategy_family"]),int(row["markets"]),int(row["variants"]),int(row["best_folds"]),int(row["folds_total"]),float(row["best_profit_factor"]),int(row["passes"]),"PASS" if int(row["passes"]) else "NO_PASS",str(row["fail_reason"] or "NO_DATA")) for row in cursor.fetchall())
                cursor.execute("""
                    SELECT p.process_id,p.run_id,p.status_code,p.progress_pct,p.current_step_code,p.requested_at,p.started_at,p.finished_at,
                           coalesce(count(s.step_run_id) FILTER (WHERE s.status_code='SUCCEEDED'),
                                    CASE WHEN p.status_code='SUCCEEDED' THEN 1 ELSE 0 END) steps_completed,
                           greatest(count(s.step_run_id),CASE WHEN p.process_type='RESEARCH_REFRESH' THEN 1 ELSE 0 END) steps_total,
                           coalesce(extract(epoch FROM (coalesce(p.finished_at,clock_timestamp())-coalesce(p.started_at,p.requested_at))),0)::int duration_seconds,
                           coalesce(p.outcome_code,p.status_code) outcome_code,
                           coalesce(p.reason_code,'ANALYSIS_PENDING') reason_code,
                           p.recommendation_code,
                           coalesce(p.explanation_ru,'Системный процесс ожидает обновления') explanation_ru,
                           coalesce(actions.items,'[]'::jsonb) available_actions
                    FROM marketcore_action.research_process_v1 p
                    LEFT JOIN analytics.edge_search_step_run_v1 s ON s.run_id=p.run_id
                    LEFT JOIN LATERAL (
                        SELECT jsonb_agg(jsonb_build_object(
                            'action_id',a.action_id,'command_code',a.command_code,
                            'policy_class',a.policy_class,'rollback_code',a.rollback_code,
                            'label',a.label,'detail',a.detail
                        ) ORDER BY a.action_order) items
                        FROM marketcore_action.research_recommendation_action_v1 a
                        WHERE a.recommendation_code=p.recommendation_code
                          AND a.locale_code='ru' AND a.enabled
                          AND p.status_code IN ('SUCCEEDED','FAILED','SKIPPED')
                    ) actions ON TRUE
                    WHERE p.actor_id <> 'test.worker'
                    GROUP BY p.process_id,actions.items
                    ORDER BY p.updated_at DESC LIMIT 10
                """)
                runs=tuple(EdgeSearchRunAuditV1(
                    str(row["process_id"]),str(row["run_id"] or ""),str(row["status_code"]),float(row["progress_pct"] or 0),str(row["current_step_code"] or "QUEUED"),int(row["steps_completed"] or 0),
                    int(row["steps_total"] or 0),int(row["duration_seconds"] or 0),str(row["outcome_code"]),
                    str(row["reason_code"]),str(row["recommendation_code"]),str(row["explanation_ru"]),
                    _utc(row["started_at"] or row["requested_at"]),tuple(dict(item) for item in row["available_actions"]),
                ) for row in cursor.fetchall())
        return ResearchSnapshotV2(str(runtime.get("status") or "UNAVAILABLE"),_count_symbols(runtime.get("active_symbols")),_count_symbols(runtime.get("failed_symbols")),_utc(runtime.get("last_cycle_at")),int(summary.get("research_candidates") or 0),int(summary.get("oos_pass") or 0),int(summary.get("paper_ready") or 0),_utc(summary.get("refreshed_at")),int(queue["total"]),int(queue["pending"]),int(queue["failed"]),_utc(queue["updated_at"]),int(oos["total"]),int(oos["passed"]),_utc(oos["updated_at"]),str(edge_search.get("status") or "NOT_RUN"),str(edge_search.get("current_step") or "NOT_RUN"),int(edge_search.get("progress_pct") or 0),int(edge_search.get("markets_evaluated") or 0),int(edge_search.get("combinations_evaluated") or 0),int(edge_search.get("oos_pass") or 0),_utc(edge_search.get("finished_at")),int(next_plan.get("item_count") or 0),int(next_plan.get("total_parameter_variants") or 0),int(edge_auto_queue.get("active") or 0),str(edge_auto_status.get("status_code") or "NEVER_RUN"),int(scout.get("discovered") or 0),int(scout.get("selected") or 0),int(scout.get("backfill") or 0),int(scout.get("watch_added") or 0),str(scout.get("status_code") or "NOT_RUN"),scout_last,scout_next,str(scout_schedule.get("run_status") or "SCHEDULED"),int(methodology.get("evaluated") or 0),int(methodology.get("passed") or 0),int(execution.get("quote_symbols") or 0),int(execution.get("spec_count") or 0),str(execution.get("quote_status") or "STALE"),str(execution.get("spec_status") or "PARTIAL"),int(governance.get("global_trials") or 0),int(governance.get("global_pass") or 0),int(holdout.get("opened") or 0),int(holdout.get("reused") or 0),int(pnl_units.get("pnl_ready") or 0),int(pnl_units.get("pnl_blocked") or 0),int(governance.get("equity_experiments") or 0),int(governance.get("futures_experiments") or 0),int(portfolio_selection.get("selected") or 0),bool(validation_funnel.get("total")),int(validation_funnel.get("in_sample") or 0),int(validation_funnel.get("oos") or 0),int(validation_funnel.get("after_costs") or 0),int(validation_funnel.get("stable") or 0),str(validation_funnel.get("bottleneck_stage") or "NO_DATA"),int(validation_funnel.get("lost_variants") or 0),str(validation_funnel.get("recommendation_code") or "NO_DATA"),strategy_degradation,methodology_failures,futures_roll_items,scout_items,universe_items,algorithms,runs,now)
