from __future__ import annotations
from datetime import datetime, timezone
import psycopg2
import psycopg2.extras
from marketcore.presentation.workspace_v2.domain.research_snapshot_v2 import EdgeSearchRunAuditV1,ResearchAlgorithmResultV2,ResearchSnapshotV2

def _utc(value):
    if value is None: return None
    return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value).astimezone(timezone.utc)

def _count_symbols(value):
    return len([item for item in str(value or "").split(",") if item.strip()])

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
        return ResearchSnapshotV2(str(runtime.get("status") or "UNAVAILABLE"),_count_symbols(runtime.get("active_symbols")),_count_symbols(runtime.get("failed_symbols")),_utc(runtime.get("last_cycle_at")),int(summary.get("research_candidates") or 0),int(summary.get("oos_pass") or 0),int(summary.get("paper_ready") or 0),_utc(summary.get("refreshed_at")),int(queue["total"]),int(queue["pending"]),int(queue["failed"]),_utc(queue["updated_at"]),int(oos["total"]),int(oos["passed"]),_utc(oos["updated_at"]),str(edge_search.get("status") or "NOT_RUN"),str(edge_search.get("current_step") or "NOT_RUN"),int(edge_search.get("progress_pct") or 0),int(edge_search.get("markets_evaluated") or 0),int(edge_search.get("combinations_evaluated") or 0),int(edge_search.get("oos_pass") or 0),_utc(edge_search.get("finished_at")),int(next_plan.get("item_count") or 0),int(next_plan.get("total_parameter_variants") or 0),int(edge_auto_queue.get("active") or 0),str(edge_auto_status.get("status_code") or "NEVER_RUN"),algorithms,runs,now)
