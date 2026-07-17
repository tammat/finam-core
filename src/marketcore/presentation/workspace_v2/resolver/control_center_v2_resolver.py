from __future__ import annotations

import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras

from marketcore.services.profit_funnel_source_registry_v2 import observe_profit_funnel_sources_v2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


class ControlCenterV2Resolver:
    def resolve(self) -> dict[str, Any]:
        with psycopg2.connect(DB) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                quality = self._quality(cur)
                relationships, summary = self._relationships(cur)
                forward = self._forward(cur)
                execution = self._execution(cur)
                execution_quality = self._execution_quality(cur)
                execution_variants = self._execution_variants(cur)
                volatility_analysis = self._volatility_analysis(cur)
                risk_analysis = self._risk_analysis(cur)
                entry_analysis = self._entry_analysis(cur)
                market_prerequisites = self._market_prerequisites(cur)
                exit_analysis = self._exit_analysis(cur)
                block_analysis = self._block_analysis(cur)
                shadow_requirements = self._shadow_requirements(cur)
                funnel_stages, loss_reasons, funnel_comparable = self._signal_funnel(cur)
                shadow = self._shadow(cur)
                shadow_process = self._shadow_process(cur)
                shadow_alerts = self._shadow_alerts(cur)
                forward_blockers = self._forward_blockers(cur)
                forward_pass_process = self._forward_pass_process(cur)
                forward_readiness = self._forward_readiness(cur)
                edge_search_process = self._edge_search_process(cur)
                edge_search_results = self._edge_search_results(cur)

        return {
            "quality": quality,
            "relationships": relationships,
            "relationship_summary": summary,
            "forward": forward,
            "execution": execution,
            "execution_quality": execution_quality,
            "execution_variants": execution_variants,
            "volatility_analysis": volatility_analysis,
            "risk_analysis": risk_analysis,
            "entry_analysis": entry_analysis,
            "market_prerequisites": market_prerequisites,
            "exit_analysis": exit_analysis,
            "block_analysis": block_analysis,
            "shadow_requirements": shadow_requirements,
            "funnel_stages": funnel_stages,
            "loss_reasons": loss_reasons,
            "funnel_comparable": funnel_comparable,
            "shadow": shadow,
            "shadow_process": shadow_process,
            "shadow_alerts": shadow_alerts,
            "forward_blockers": forward_blockers,
            "forward_pass_process": forward_pass_process,
            "forward_readiness": forward_readiness,
            "edge_search_process": edge_search_process,
            "edge_search_results": edge_search_results,
        }

    @staticmethod
    def _quality(cur) -> dict[str, Any]:
        cur.execute("""
            SELECT count(*) AS total,
                   count(*) FILTER (WHERE factory_status='READY') AS ready
            FROM analytics.relationship_data_quality_gate_v1
            WHERE audit_run_id=(
                SELECT audit_run_id FROM analytics.relationship_data_quality_gate_v1
                ORDER BY created_at DESC LIMIT 1
            )
        """)
        return dict(cur.fetchone() or {"total": 0, "ready": 0})

    @staticmethod
    def _relationships(cur) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        cur.execute("""
            SELECT discovery_run_id
            FROM analytics.relationship_factory_result_v2
            ORDER BY created_at DESC LIMIT 1
        """)
        latest = cur.fetchone()
        if not latest:
            return [], {"trials": 0, "relationships": 0, "passed": 0, "failed": 0, "unverified": 0}

        run_id = latest["discovery_run_id"]
        cur.execute("""
            SELECT count(*) AS trials,
                   count(DISTINCT relationship_code) AS relationships,
                   count(*) FILTER (WHERE verdict_code='OOS_PASS') AS passed,
                   count(*) FILTER (WHERE verdict_code='OOS_FAIL') AS failed,
                   count(*) FILTER (WHERE verdict_code='UNVERIFIED') AS unverified
            FROM analytics.relationship_factory_result_v2
            WHERE discovery_run_id=%s
        """, (run_id,))
        summary = dict(cur.fetchone() or {})

        cur.execute("""
            SELECT relationship_family,source_symbols,target_symbol,regime_group,session_code,
                   oos_trades,oos_profit_factor,oos_expectancy_bps,regime_coverage_ratio,
                   verdict_code
            FROM analytics.relationship_factory_result_v2
            WHERE discovery_run_id=%s
            ORDER BY CASE verdict_code WHEN 'OOS_PASS' THEN 1 WHEN 'OOS_FAIL' THEN 2 ELSE 3 END,
                     adjusted_p_value,oos_profit_factor DESC,oos_trades DESC
            LIMIT 12
        """, (run_id,))
        return [dict(row) for row in cur.fetchall()], summary

    @staticmethod
    def _forward(cur) -> dict[str, Any]:
        cur.execute("SELECT analytics.forward_edge_baseline_cohort_id_v1() AS cohort_id")
        latest = cur.fetchone()
        if not latest:
            return {"candidates": 0, "observations": 0, "promoted": 0}
        cur.execute("""
            SELECT count(*) AS candidates,
                   count(*) FILTER (WHERE promotion_allowed) AS promoted
            FROM analytics.forward_edge_incubator_v1 WHERE cohort_id=%s
        """, (latest["cohort_id"],))
        result = dict(cur.fetchone() or {})
        cur.execute("SELECT count(*) AS observations FROM analytics.forward_edge_observation_v1 WHERE cohort_id=%s", (latest["cohort_id"],))
        result.update(dict(cur.fetchone() or {}))
        return result

    @staticmethod
    def _execution(cur) -> dict[str, Any]:
        cur.execute("""
            SELECT count(*) AS trials,
                   count(*) FILTER (WHERE market_data_quality='QUOTE_VERIFIED') AS quote_verified
            FROM analytics.execution_edge_result_v1
            WHERE discovery_run_id=(
                SELECT discovery_run_id FROM analytics.execution_edge_result_v1
                ORDER BY created_at DESC LIMIT 1
            )
        """)
        return dict(cur.fetchone() or {"trials": 0, "quote_verified": 0})

    @staticmethod
    def _execution_quality(cur) -> list[dict[str, Any]]:
        cur.execute("""
            SELECT 'PAPER' AS mode,
                   count(*) AS fills,
                   count(f.fill_id) AS linked_fills,
                   coalesce(sum(f.commission),0) AS commission,
                   CASE WHEN count(*) > 0
                        THEN 100.0 * count(f.fill_id) / count(*) ELSE 0 END AS linkage_pct,
                   count(*) > 0 AND count(*) FILTER (
                       WHERE ms.snapshot_id IS NOT NULL
                   ) = count(*) AS quotes_verified,
                   count(*) FILTER (WHERE sf.side='BUY') AS positions_opened,
                   (SELECT count(*) FROM public.trailing_order_events
                    WHERE ts >= date_trunc('day',now()) AND action='PLACE_STOP') AS stops_placed,
                   (SELECT count(*) FROM public.position_lifecycle_state
                    WHERE trailing_active AND remaining_qty > 0
                      AND EXISTS (
                          SELECT 1 FROM public.signal_fills current_fill
                          WHERE current_fill.created_at >= date_trunc('day',now())
                            AND current_fill.symbol=position_lifecycle_state.symbol
                      )) AS trailing_active,
                   (SELECT count(*) FROM public.trailing_order_events
                    WHERE ts >= date_trunc('day',now()) AND action='REPLACE_STOP') AS stops_improved,
                   (SELECT count(*) FROM public.profit_lock_events
                    WHERE ts >= date_trunc('day',now()) AND action <> 'HOLD') AS profit_locks,
                   (SELECT count(*) FROM public.take_profit_events
                    WHERE ts >= date_trunc('day',now()) AND action <> 'HOLD') AS take_profits,
                   count(*) FILTER (WHERE sf.side='SELL') AS positions_closed
            FROM public.signal_fills sf
            LEFT JOIN public.fills f ON f.fill_id=sf.fill_id
            LEFT JOIN LATERAL (
                SELECT snapshot_id
                FROM analytics.market_microstructure_snapshot_v1 s
                WHERE s.symbol=sf.symbol
                  AND s.observed_at BETWEEN coalesce(f.ts,sf.created_at)-interval '30 seconds'
                                        AND coalesce(f.ts,sf.created_at)+interval '30 seconds'
                  AND s.best_bid > 0 AND s.best_ask > s.best_bid
                  AND s.bid_levels > 0 AND s.ask_levels > 0
                  AND abs(extract(epoch FROM (
                      coalesce(s.exchange_ts,s.observed_at)-coalesce(f.ts,sf.created_at)
                  ))) <= 5
                ORDER BY abs(extract(epoch FROM (
                    coalesce(s.exchange_ts,s.observed_at)-coalesce(f.ts,sf.created_at)
                ))), s.snapshot_id DESC
                LIMIT 1
            ) ms ON true
            WHERE sf.created_at >= date_trunc('day', now())
            UNION ALL
            SELECT 'SHADOW', count(*), count(*),
                   coalesce(sum(t.commission),0),
                   CASE WHEN count(*) > 0 THEN 100.0 ELSE 0 END,
                   count(*) > 0 AND count(*) FILTER (
                       WHERE ms.snapshot_id IS NOT NULL
                   ) = count(*),
                   count(*) FILTER (WHERE t.side IN ('BUY','LONG')),0,0,0,0,0,
                   count(*) FILTER (WHERE t.shadow_status='CLOSED')
            FROM analytics.forward_pass_shadow_observation_v1 t
            LEFT JOIN LATERAL (
                SELECT snapshot_id
                FROM analytics.market_microstructure_snapshot_v1 s
                WHERE (s.symbol=t.symbol OR (
                    position('@' IN t.symbol)=0 AND s.symbol=t.symbol||'@MISX'
                ))
                  AND t.entry_ts IS NOT NULL
                  AND s.observed_at BETWEEN t.entry_ts-interval '30 seconds'
                                        AND t.entry_ts+interval '30 seconds'
                  AND s.best_bid > 0 AND s.best_ask > s.best_bid
                  AND s.bid_levels > 0 AND s.ask_levels > 0
                  AND abs(extract(epoch FROM (
                      coalesce(s.exchange_ts,s.observed_at)-t.entry_ts
                  ))) <= 5
                ORDER BY abs(extract(epoch FROM (
                    coalesce(s.exchange_ts,s.observed_at)-t.entry_ts
                ))), s.snapshot_id DESC
                LIMIT 1
            ) ms ON true
            WHERE t.cohort_id=(
                SELECT cohort_id FROM analytics.forward_pass_shadow_observation_v1
                ORDER BY created_at DESC LIMIT 1
            ) AND t.entry_ts IS NOT NULL
        """)
        return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def _execution_variants(cur) -> list[dict[str, Any]]:
        cur.execute("""
            SELECT policy_code, parameter_json, oos_trades, folds_passed, folds_total,
                   delta_profit_factor, delta_expectancy, market_data_quality,
                   verdict_code, reason_code, promotion_allowed
            FROM analytics.execution_edge_result_v1
            WHERE discovery_run_id=(
                SELECT discovery_run_id FROM analytics.execution_edge_result_v1
                ORDER BY created_at DESC LIMIT 1
            )
            ORDER BY promotion_allowed DESC, adjusted_p_value,
                     folds_passed DESC, delta_expectancy DESC
            LIMIT 8
        """)
        return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def _volatility_analysis(cur) -> list[dict[str, Any]]:
        cur.execute("""
            SELECT regime_group, count(*) AS trials,
                   sum(oos_trades) AS oos_trades,
                   round(avg(oos_profit_factor),3) AS profit_factor,
                   round(avg(oos_expectancy_bps),3) AS expectancy_bps,
                   count(*) FILTER (WHERE verdict_code='OOS_PASS') AS passed
            FROM analytics.relationship_factory_result_v2
            WHERE discovery_run_id=(
                SELECT discovery_run_id FROM analytics.relationship_factory_result_v2
                ORDER BY created_at DESC LIMIT 1
            )
            GROUP BY regime_group
            ORDER BY passed DESC, expectancy_bps DESC NULLS LAST
        """)
        return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def _risk_analysis(cur) -> list[dict[str, Any]]:
        cur.execute("""
            WITH active_contracts AS (
                SELECT DISTINCT symbol FROM public.signal_fills
                WHERE created_at >= date_trunc('day',now())
            )
            SELECT a.symbol,coalesce(r.strategy_family,'—') AS strategy_family,
                   r.signal_ts,coalesce(r.risk_score,0) AS risk_score,
                   coalesce(r.position_risk_score,0) AS position_risk_score,
                   coalesce(r.exposure_risk_score,0) AS exposure_risk_score,
                   coalesce(r.daily_loss_risk_score,0) AS daily_loss_risk_score,
                   coalesce(r.correlation_risk_score,0) AS correlation_risk_score,
                   coalesce(r.risk_decision_code,'NO_CURRENT_RISK_SNAPSHOT') AS risk_decision_code,
                   coalesce(r.recommendation_code,'REBUILD_RISK_SNAPSHOT') AS recommendation_code,
                   coalesce(r.ready_for_paper,false) AS ready_for_paper,r.refreshed_at
            FROM active_contracts a
            LEFT JOIN LATERAL (
                SELECT * FROM analytics.risk_decision_snapshot_v1 d
                WHERE d.symbol=a.symbol ORDER BY refreshed_at DESC LIMIT 1
            ) r ON true
            ORDER BY a.symbol
        """)
        return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def _entry_analysis(cur) -> list[dict[str, Any]]:
        cur.execute("""
            WITH latest AS (
                SELECT discovery_run_id
                FROM analytics.execution_edge_result_v1
                ORDER BY created_at DESC LIMIT 1
            ), visible_variants AS (
                SELECT strategy_code, symbol, timeframe, parameter_json,
                       regime_code, session_code, policy_code,
                       oos_trades, oos_profit_factor, oos_expectancy,
                       folds_passed, folds_total, verdict_code, reason_code,
                       promotion_allowed, adjusted_p_value,
                       row_number() OVER (
                           PARTITION BY strategy_code, symbol, timeframe, parameter_json
                           ORDER BY promotion_allowed DESC, adjusted_p_value,
                                    folds_passed DESC, oos_expectancy DESC,
                                    regime_code, session_code, policy_code
                       ) AS visible_rank
                FROM analytics.execution_edge_result_v1
                WHERE discovery_run_id=(SELECT discovery_run_id FROM latest)
            )
            SELECT strategy_code, symbol, timeframe, parameter_json,
                   regime_code, session_code, policy_code, oos_trades,
                   oos_profit_factor, oos_expectancy, folds_passed, folds_total,
                   verdict_code, reason_code, promotion_allowed
            FROM visible_variants
            WHERE visible_rank=1
            ORDER BY promotion_allowed DESC, adjusted_p_value,
                     folds_passed DESC, oos_expectancy DESC
            LIMIT 12
        """)
        return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def _market_prerequisites(cur) -> list[dict[str, Any]]:
        cur.execute("""
            SELECT symbol,timeframe,bars,trading_days,latest_age_hours,
                   regime_coverage_ratio,market_data_status,factory_status,reason_codes
            FROM analytics.relationship_data_quality_gate_v1
            WHERE audit_run_id=(SELECT audit_run_id FROM analytics.relationship_data_quality_gate_v1 ORDER BY created_at DESC LIMIT 1)
            ORDER BY factory_status DESC,latest_age_hours DESC,symbol
        """)
        return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def _exit_analysis(cur) -> list[dict[str, Any]]:
        cur.execute("""
            SELECT policy_code,count(*) AS variants,
                   count(*) FILTER (WHERE variant_status='CLOSED') AS closed,
                   round(avg(extract(epoch FROM (exit_ts-entry_ts))/60) FILTER (WHERE exit_ts IS NOT NULL),1) AS avg_hold_minutes,
                   coalesce(sum(net_pnl) FILTER (WHERE variant_status='CLOSED'),0) AS net_pnl,
                   count(*) FILTER (WHERE exit_reason='TRAILING_STOP') AS trailing_exits,
                   count(*) FILTER (WHERE broker_order_sent OR runtime_allowed OR execution_enabled) AS unsafe
            FROM analytics.forward_edge_shadow_exit_variant_v1
            WHERE cohort_id=analytics.forward_edge_baseline_cohort_id_v1()
            GROUP BY policy_code ORDER BY net_pnl DESC
        """)
        return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def _block_analysis(cur) -> list[dict[str, Any]]:
        cur.execute("""
            SELECT reason_value,rows_total,source_table,reason_column,evidence_json
            FROM analytics.signal_funnel_reason_v1
            WHERE signal_funnel_reason_snapshot_id=(SELECT signal_funnel_reason_snapshot_id FROM analytics.signal_funnel_reason_snapshot_v1 ORDER BY created_at DESC LIMIT 1)
              AND reason_group='BLOCK'
            ORDER BY rows_total DESC LIMIT 20
        """)
        return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def _shadow_requirements(cur) -> list[dict[str, Any]]:
        cur.execute("""
            SELECT c.symbol,c.timeframe,s.decision_code,s.closed_trades,s.calendar_days,
                   s.profit_factor,s.expectancy,s.max_drawdown,s.cost_coverage,
                   s.tested_regimes,s.positive_regime_share,s.progress_pct,s.reason_codes,
                   p.minimum_closed,p.minimum_calendar_days,p.minimum_profit_factor,
                   p.minimum_cost_coverage,s.evaluated_at
            FROM analytics.shadow_pass_status_v1 s
            JOIN analytics.forward_pass_shadow_candidate_v1 c USING(shadow_candidate_id)
            JOIN analytics.shadow_pass_policy_v1 p ON p.policy_code=s.policy_code
            ORDER BY s.decision_code,c.symbol
        """)
        return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def _signal_funnel(cur) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
        observations = observe_profit_funnel_sources_v2(DB)
        cur.execute("""
            SELECT transition_code,to_stage,from_count,to_count,lineage_status,reason_code
            FROM analytics.profit_funnel_transition_lineage_v2
        """)
        transitions = {row["to_stage"]: dict(row) for row in cur.fetchall()}
        now = datetime.now(timezone.utc)
        stages: list[dict[str, Any]] = []
        for stage_order, observation in enumerate(observations, start=1):
            incoming = transitions.get(observation.stage.value)
            age_seconds = None if observation.source_as_of is None else max(
                0, int((now - observation.source_as_of).total_seconds())
            )
            freshness = "UNAVAILABLE" if age_seconds is None else ("CURRENT" if age_seconds <= 7200 else "STALE")
            pass_rate = None
            reason_code = "INITIAL_STAGE"
            lineage_status = "PROVEN"
            if incoming:
                reason_code = incoming["reason_code"]
                lineage_status = incoming["lineage_status"]
                if lineage_status == "PROVEN" and incoming["from_count"]:
                    pass_rate = 100.0 * incoming["to_count"] / incoming["from_count"]
            status = "OK"
            if freshness == "UNAVAILABLE" or observation.stage.value in {"LIVE", "PROFIT"}:
                status = "BLOCKED"
            elif freshness != "CURRENT" or lineage_status != "PROVEN" or observation.quality_code != "VERIFIED":
                status = "WARNING"
            stages.append({
                "stage_order": stage_order,
                "stage_code": observation.stage.value,
                "stage_name": observation.stage.value,
                "stage_count": observation.count,
                "previous_stage_count": incoming["from_count"] if incoming else None,
                "pass_rate_pct": pass_rate,
                "stage_status": status,
                "source_identity": observation.source_identity,
                "source_as_of": observation.source_as_of,
                "freshness_code": freshness,
                "quality_code": observation.quality_code,
                "reason_code": reason_code,
                "net_pnl": observation.net_pnl,
                "cost_impact": observation.cost_impact,
            })
        unverified = [row for row in transitions.values() if row["lineage_status"] != "PROVEN"]
        reasons = ([{
            "reason_group": "LIFECYCLE",
            "rows_total": len(unverified),
            "reason_values": len({row["reason_code"] for row in unverified}),
            "action_target": "/workspace-v2/control-center",
        }] if unverified else [])
        return stages, reasons, not unverified

    @staticmethod
    def _shadow(cur) -> dict[str, Any]:
        cur.execute("""
            SELECT count(*) total,count(*) FILTER (WHERE shadow_status='PENDING_ENTRY') pending,
                   count(*) FILTER (WHERE shadow_status='OPEN') open,
                   count(*) FILTER (WHERE shadow_status='CLOSED') closed,
                   coalesce(sum(net_pnl) FILTER (WHERE shadow_status='CLOSED'),0) net_pnl,
                   count(*) FILTER (WHERE broker_order_sent OR runtime_allowed OR execution_enabled) unsafe,
                   max(updated_at) source_as_of
            FROM analytics.forward_pass_shadow_observation_v1
        """)
        return dict(cur.fetchone() or {})

        # Legacy implementation intentionally retained below for schema history; unreachable in V2.
        cur.execute("SELECT to_regclass('analytics.forward_edge_shadow_trade_v1') AS table_name")
        if not cur.fetchone()["table_name"]:
            return {"total": 0, "pending": 0, "open": 0, "closed": 0, "net_pnl": 0, "unsafe": 0}
        cur.execute("SELECT analytics.forward_edge_baseline_cohort_id_v1() AS cohort_id")
        latest = cur.fetchone()
        if not latest:
            return {"total": 0, "pending": 0, "open": 0, "closed": 0, "net_pnl": 0, "unsafe": 0}
        active_cohort_id = latest["cohort_id"]
        cur.execute("""
            SELECT count(*) AS observations
            FROM analytics.forward_edge_observation_v1
            WHERE cohort_id=%s
        """, (active_cohort_id,))
        active_observations = int((cur.fetchone() or {}).get("observations") or 0)
        cur.execute("""
            SELECT i.cohort_id
            FROM analytics.forward_edge_incubator_v1 i
            WHERE EXISTS (
                SELECT 1 FROM analytics.forward_edge_shadow_trade_v1 t
                WHERE t.cohort_id=i.cohort_id
            )
            ORDER BY i.created_at DESC
            LIMIT 1
        """)
        reporting = cur.fetchone() or latest
        reporting_cohort_id = reporting["cohort_id"]
        cur.execute("""
            WITH ranked AS (
                SELECT t.*,row_number() OVER (
                    PARTITION BY symbol,signal_ts,entry_ts,exit_ts,side,
                                 entry_price,exit_price,shadow_status
                    ORDER BY created_at,shadow_trade_id
                ) AS execution_path_rank
                FROM analytics.forward_edge_shadow_trade_v1 t
                WHERE cohort_id=%s
            )
            SELECT count(*) total,count(*) FILTER (WHERE shadow_status='PENDING_ENTRY') pending,
                   count(*) FILTER (WHERE shadow_status='OPEN') open,count(*) FILTER (WHERE shadow_status='CLOSED') closed,
                   coalesce(sum(net_pnl) FILTER (WHERE shadow_status='CLOSED'),0) net_pnl,
                   count(*) FILTER (WHERE broker_order_sent OR runtime_allowed OR execution_enabled) unsafe
            FROM ranked WHERE execution_path_rank=1
        """, (reporting_cohort_id,))
        result = dict(cur.fetchone() or {})
        result.update({
            "active_cohort_id": str(active_cohort_id),
            "active_observations": active_observations,
            "reporting_cohort_id": str(reporting_cohort_id),
            "reporting_is_archived": reporting_cohort_id != active_cohort_id,
        })
        cur.execute("""
            WITH ranked AS (
                SELECT i.strategy_family,t.*,o.regime_code,o.session_code,o.data_quality_status,
                       row_number() OVER (
                    PARTITION BY i.strategy_family,t.symbol,t.signal_ts,t.entry_ts,t.exit_ts,
                                 t.side,t.entry_price,t.exit_price,t.shadow_status
                    ORDER BY t.created_at,t.shadow_trade_id
                ) AS family_path_rank
                FROM analytics.forward_edge_shadow_trade_v1 t
                JOIN analytics.forward_edge_incubator_v1 i
                  USING (cohort_id,incubator_candidate_id)
                JOIN analytics.forward_edge_observation_v1 o USING (observation_id)
                WHERE t.cohort_id=%s
            ), family_summary AS (
                SELECT strategy_family,
                       count(*) FILTER (WHERE shadow_status='CLOSED') AS closed_paths,
                       count(*) FILTER (
                           WHERE shadow_status='CLOSED'
                             AND regime_code IS NOT NULL AND session_code IS NOT NULL
                             AND data_quality_status='VERIFIED'
                             AND (coalesce(spread_cost,0)<>0 OR coalesce(slippage,0)<>0)
                       ) AS quality_ready_paths,
                       coalesce(sum(net_pnl) FILTER (WHERE shadow_status='CLOSED'),0) AS net_pnl
                FROM ranked WHERE family_path_rank=1
                GROUP BY strategy_family
            )
            SELECT
                count(*) FILTER (
                    WHERE closed_paths>0 AND net_pnl>0 AND quality_ready_paths=closed_paths
                ) AS eligible_families,
                coalesce(sum(closed_paths) FILTER (
                    WHERE closed_paths>0 AND net_pnl>0 AND quality_ready_paths=closed_paths
                ),0) AS eligible_closed,
                coalesce(sum(net_pnl) FILTER (
                    WHERE closed_paths>0 AND net_pnl>0 AND quality_ready_paths=closed_paths
                ),0) AS eligible_net_pnl,
                count(*) FILTER (
                    WHERE closed_paths>0 AND net_pnl>0 AND quality_ready_paths<closed_paths
                ) AS quality_pending_families,
                coalesce(sum(closed_paths) FILTER (
                    WHERE closed_paths>0 AND net_pnl>0 AND quality_ready_paths<closed_paths
                ),0) AS quality_pending_closed,
                coalesce(sum(net_pnl) FILTER (
                    WHERE closed_paths>0 AND net_pnl>0 AND quality_ready_paths<closed_paths
                ),0) AS quality_pending_net_pnl,
                count(*) FILTER (WHERE closed_paths>0 AND net_pnl<=0) AS exploratory_families,
                coalesce(sum(closed_paths) FILTER (WHERE closed_paths>0 AND net_pnl<=0),0) AS exploratory_closed,
                coalesce(sum(net_pnl) FILTER (WHERE closed_paths>0 AND net_pnl<=0),0) AS exploratory_net_pnl,
                string_agg(strategy_family,', ' ORDER BY strategy_family)
                    FILTER (
                        WHERE closed_paths>0 AND net_pnl>0 AND quality_ready_paths=closed_paths
                    ) AS eligible_family_names,
                string_agg(strategy_family,', ' ORDER BY strategy_family)
                    FILTER (
                        WHERE closed_paths>0 AND net_pnl>0 AND quality_ready_paths<closed_paths
                    ) AS quality_pending_family_names,
                string_agg(strategy_family,', ' ORDER BY strategy_family)
                    FILTER (WHERE closed_paths>0 AND net_pnl<=0) AS exploratory_family_names
            FROM family_summary
        """, (reporting_cohort_id,))
        result.update(dict(cur.fetchone() or {}))
        cur.execute("SELECT to_regclass('analytics.forward_edge_shadow_exit_variant_v1') AS table_name")
        if cur.fetchone()["table_name"]:
            cur.execute("""
                WITH ranked AS (
                    SELECT v.*,row_number() OVER (
                        PARTITION BY policy_code,symbol,entry_ts,exit_ts,side,
                                     entry_price,exit_price,variant_status
                        ORDER BY created_at,variant_id
                    ) AS execution_path_rank
                    FROM analytics.forward_edge_shadow_exit_variant_v1 v
                    WHERE cohort_id=%s AND policy_code='ATR_TRAIL_14_2_5'
                )
                SELECT count(*) trailing_total,
                       count(*) FILTER (WHERE variant_status='OPEN') trailing_open,
                       count(*) FILTER (WHERE variant_status='CLOSED') trailing_closed,
                       count(*) FILTER (WHERE exit_reason='TRAILING_STOP') trailing_exits,
                       coalesce(sum(net_pnl) FILTER (WHERE variant_status='CLOSED'),0) trailing_net_pnl,
                       count(*) FILTER (WHERE broker_order_sent OR runtime_allowed OR execution_enabled) trailing_unsafe
                FROM ranked WHERE execution_path_rank=1
            """, (reporting_cohort_id,))
            result.update(dict(cur.fetchone() or {}))
        cur.execute("SELECT to_regclass('analytics.shadow_experiment_guard_check_v1') AS table_name")
        if cur.fetchone()["table_name"]:
            cur.execute("""
                SELECT check_status,cron_ready,worker_log_ready,websocket_connected,
                       disk_used_pct,memory_available_mb,reasons_json,created_at
                FROM analytics.shadow_experiment_guard_check_v1
                ORDER BY created_at DESC LIMIT 1
            """)
            guard = dict(cur.fetchone() or {})
            result.update({f"guard_{key}": value for key, value in guard.items()})
        return result

    @staticmethod
    def _shadow_process(cur) -> list[dict[str, Any]]:
        cur.execute("SELECT count(*) count,max(updated_at) updated_at FROM analytics.forward_edge_regime_promotion_gate_v1 WHERE decision_code='READY_FOR_PAPER_REVIEW' AND review_eligible")
        forward=dict(cur.fetchone() or {})
        cur.execute("SELECT * FROM analytics.forward_pass_shadow_heartbeat_v1 WHERE worker_code='FORWARD_PASS_SHADOW_OBSERVER'")
        heartbeat=dict(cur.fetchone() or {})
        cur.execute("SELECT count(*) count,coalesce(max(progress_pct),0) progress_pct,max(evaluated_at) updated_at,count(*) FILTER(WHERE decision_code='PASS') passed FROM analytics.shadow_pass_status_v1")
        shadow=dict(cur.fetchone() or {})
        cur.execute("SELECT count(*) count,max(updated_at) updated_at FROM analytics.forward_pass_paper_candidate_v1 WHERE paper_allowed")
        paper=dict(cur.fetchone() or {})
        return [
            {"step_code":"FORWARD_PASS","status":"PASS" if forward.get("count") else "WAITING","progress_pct":100 if forward.get("count") else 0,"count":forward.get("count",0),"reason_code":"FORWARD_PASS_CONFIRMED" if forward.get("count") else "NO_FORWARD_PASS","updated_at":forward.get("updated_at")},
            {"step_code":"SHADOW_OBSERVER","status":heartbeat.get("status_code","NEVER_RUN"),"progress_pct":100 if heartbeat.get("status_code")=="HEALTHY" else 0,"count":heartbeat.get("candidates_active",0),"reason_code":heartbeat.get("last_error_code") or "SHADOW_HEARTBEAT_OK","updated_at":heartbeat.get("updated_at")},
            {"step_code":"SHADOW_PASS","status":"PASS" if shadow.get("passed") else "WAITING","progress_pct":shadow.get("progress_pct",0),"count":shadow.get("passed",0),"reason_code":"SHADOW_PASS_CONFIRMED" if shadow.get("passed") else "SHADOW_EVIDENCE_PENDING","updated_at":shadow.get("updated_at")},
            {"step_code":"PAPER_CANDIDATE","status":"READY" if paper.get("count") else "WAITING","progress_pct":100 if paper.get("count") else 0,"count":paper.get("count",0),"reason_code":"PAPER_CANDIDATE_READY" if paper.get("count") else "AWAITING_SHADOW_PASS","updated_at":paper.get("updated_at")},
        ]

    @staticmethod
    def _shadow_alerts(cur) -> list[dict[str, Any]]:
        cur.execute("SELECT severity_code,status_code,alert_code,reason_code,opened_at,updated_at FROM analytics.shadow_pipeline_alert_v1 WHERE status_code='OPEN' ORDER BY CASE severity_code WHEN 'CRITICAL' THEN 1 WHEN 'WARNING' THEN 2 ELSE 3 END,opened_at")
        return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def _forward_blockers(cur) -> list[dict[str, Any]]:
        cur.execute("""SELECT reason.value reason_code,count(*) count,max(g.updated_at) updated_at
            FROM analytics.forward_edge_regime_promotion_gate_v1 g
            CROSS JOIN LATERAL jsonb_array_elements_text(g.reason_codes) reason(value)
            WHERE g.decision_code='HOLD_RESEARCH' GROUP BY reason.value ORDER BY count(*) DESC,reason.value""")
        return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def _forward_pass_process(cur) -> list[dict[str, Any]]:
        cur.execute("""SELECT step_order,step_code,status_code,progress_pct,item_count,
                       reason_code,source_as_of
                FROM analytics.forward_pass_stage_status_v1 ORDER BY step_order""")
        return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def _forward_readiness(cur) -> list[dict[str, Any]]:
        cur.execute("""SELECT readiness_rank,policy_code,closed_observations,calendar_days,
                       tested_regimes,overall_progress_pct,decision_code,reason_codes
                FROM analytics.forward_pass_readiness_v1 ORDER BY readiness_rank LIMIT 10""")
        return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def _edge_search_process(cur) -> list[dict[str, Any]]:
        cur.execute("""SELECT l.run_id,q.status FROM marketcore_action.command_request_v2 q
            LEFT JOIN marketcore_action.edge_search_request_run_v1 l USING(request_id)
            WHERE q.request_kind='EDGE_SEARCH_RUN' ORDER BY q.requested_at DESC LIMIT 1""")
        latest=cur.fetchone()
        run_id=latest["run_id"] if latest and latest["status"] not in ('PENDING','CANCELLED') else None
        cur.execute("""SELECT p.step_order,p.title_ru step,
                   coalesce(r.status_code,'PENDING') status_code,
                   CASE coalesce(r.status_code,'PENDING') WHEN 'SUCCEEDED' THEN 100 WHEN 'RUNNING' THEN 50 ELSE 0 END progress_pct,
                   r.duration_ms,
                   coalesce((r.metrics->>'markets')::integer,0) markets_evaluated,
                   coalesce((r.metrics->>'candidates_evaluated')::integer,0) combinations_evaluated,
                   coalesce((r.metrics->>'oos_pass')::integer,0) oos_pass
            FROM analytics.edge_search_scenario_step_v1 p
            LEFT JOIN analytics.edge_search_step_run_v1 r ON r.run_id=%s AND r.step_order=p.step_order
            WHERE p.scenario_code='AUTONOMOUS_EDGE_SEARCH' AND p.enabled ORDER BY p.step_order""",(run_id,))
        return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def _edge_search_results(cur) -> list[dict[str, Any]]:
        cur.execute("""WITH request AS (
                   SELECT q.request_id,q.status,q.requested_at,l.cycle_id,l.run_id
                   FROM marketcore_action.command_request_v2 q
                   LEFT JOIN marketcore_action.edge_search_request_run_v1 l USING(request_id)
                   WHERE q.request_kind='EDGE_SEARCH_RUN' ORDER BY q.requested_at DESC LIMIT 1)
            SELECT request.status command_status,request.requested_at,
                   c.status_code,c.current_step,c.progress_pct,c.markets_evaluated,
                   c.combinations_evaluated,c.oos_pass,c.reason_code,c.started_at,c.finished_at,
                   a.outcome_code,a.recommendation_code,a.explanation_ru
            FROM request LEFT JOIN analytics.edge_search_cycle_status_v1 c ON c.cycle_id=request.cycle_id
            LEFT JOIN analytics.edge_search_scenario_run_v1 r ON r.run_id=request.run_id
            LEFT JOIN analytics.edge_search_run_analysis_v1 a ON a.run_id=request.run_id
            LIMIT 1""")
        row=cur.fetchone()
        return [dict(row)] if row else []
