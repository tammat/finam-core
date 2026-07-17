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
                    SELECT r.run_id,r.status_code,r.started_at,r.finished_at,
                           count(s.step_run_id) FILTER (WHERE s.status_code='SUCCEEDED') steps_completed,
                           count(s.step_run_id) steps_total,
                           coalesce(extract(epoch FROM (coalesce(r.finished_at,clock_timestamp())-r.started_at)),0)::int duration_seconds,
                           coalesce(a.outcome_code,r.status_code) outcome_code,
                           coalesce(a.primary_reason_code,'ANALYSIS_PENDING') reason_code,
                           coalesce(a.recommendation_code,'WAIT_FOR_SYSTEM_ANALYSIS') recommendation_code,
                           coalesce(a.explanation_ru,'Системный анализ ещё не завершён') explanation_ru
                    FROM analytics.edge_search_scenario_run_v1 r
                    LEFT JOIN analytics.edge_search_step_run_v1 s ON s.run_id=r.run_id
                    LEFT JOIN analytics.edge_search_run_analysis_v1 a ON a.run_id=r.run_id
                    GROUP BY r.run_id,a.outcome_code,a.primary_reason_code,a.recommendation_code,a.explanation_ru
                    ORDER BY r.started_at DESC LIMIT 10
                """)
                runs=tuple(EdgeSearchRunAuditV1(
                    str(row["run_id"]),str(row["status_code"]),int(row["steps_completed"] or 0),
                    int(row["steps_total"] or 0),int(row["duration_seconds"] or 0),str(row["outcome_code"]),
                    str(row["reason_code"]),str(row["recommendation_code"]),str(row["explanation_ru"]),
                    _utc(row["started_at"]),
                ) for row in cursor.fetchall())
        return ResearchSnapshotV2(str(runtime.get("status") or "UNAVAILABLE"),_count_symbols(runtime.get("active_symbols")),_count_symbols(runtime.get("failed_symbols")),_utc(runtime.get("last_cycle_at")),int(summary.get("research_candidates") or 0),int(summary.get("oos_pass") or 0),int(summary.get("paper_ready") or 0),_utc(summary.get("refreshed_at")),int(queue["total"]),int(queue["pending"]),int(queue["failed"]),_utc(queue["updated_at"]),int(oos["total"]),int(oos["passed"]),_utc(oos["updated_at"]),str(edge_search.get("status") or "NOT_RUN"),str(edge_search.get("current_step") or "NOT_RUN"),int(edge_search.get("progress_pct") or 0),int(edge_search.get("markets_evaluated") or 0),int(edge_search.get("combinations_evaluated") or 0),int(edge_search.get("oos_pass") or 0),_utc(edge_search.get("finished_at")),algorithms,runs,now)
