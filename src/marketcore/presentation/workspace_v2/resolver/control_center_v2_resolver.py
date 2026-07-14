from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras


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
        cur.execute("SELECT cohort_id FROM analytics.forward_edge_incubator_v1 ORDER BY created_at DESC LIMIT 1")
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
                    WHERE trailing_active AND remaining_qty > 0) AS trailing_active,
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
            FROM analytics.forward_edge_shadow_trade_v1 t
            LEFT JOIN LATERAL (
                SELECT snapshot_id
                FROM analytics.market_microstructure_snapshot_v1 s
                WHERE (s.symbol=t.symbol OR (
                    position('@' IN t.symbol)=0 AND s.symbol=t.symbol||'@MISX'
                ))
                  AND t.entry_ts IS NOT NULL
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
                SELECT cohort_id FROM analytics.forward_edge_shadow_trade_v1
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
            SELECT strategy_code, symbol, timeframe, parameter_json,
                   regime_code, session_code, oos_trades, oos_profit_factor,
                   oos_expectancy, folds_passed, folds_total,
                   verdict_code, reason_code, promotion_allowed
            FROM analytics.execution_edge_result_v1
            WHERE discovery_run_id=(
                SELECT discovery_run_id FROM analytics.execution_edge_result_v1
                ORDER BY created_at DESC LIMIT 1
            )
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
            WHERE cohort_id=(SELECT cohort_id FROM analytics.forward_edge_incubator_v1 ORDER BY created_at DESC LIMIT 1)
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
        policy_path = Path("config/research/swing_forward_shadow_policy_v1.json")
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        cur.execute("""
            SELECT timeframe,
                   count(*) FILTER (WHERE shadow_status='CLOSED') AS closed,
                   count(DISTINCT signal_ts::date) AS sessions
            FROM analytics.forward_edge_shadow_trade_v1
            WHERE cohort_id=(SELECT cohort_id FROM analytics.forward_edge_incubator_v1 ORDER BY created_at DESC LIMIT 1)
            GROUP BY timeframe ORDER BY timeframe
        """)
        result = []
        for row in cur.fetchall():
            item = dict(row)
            item["minimum_closed"] = int(policy["minimum_closed_per_timeframe"])
            item["minimum_sessions"] = int(policy["minimum_trading_sessions"])
            item["missing_closed"] = max(0, item["minimum_closed"] - int(item.get("closed") or 0))
            item["missing_sessions"] = max(0, item["minimum_sessions"] - int(item.get("sessions") or 0))
            result.append(item)
        return result

    @staticmethod
    def _signal_funnel(cur) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
        cur.execute("SELECT signal_funnel_snapshot_id FROM analytics.signal_funnel_snapshot_v1 ORDER BY created_at DESC LIMIT 1")
        latest = cur.fetchone()
        stages: list[dict[str, Any]] = []
        if latest:
            cur.execute("""
                SELECT stage_order,stage_code,stage_name,stage_count,previous_stage_count,
                       pass_rate_pct,stage_status,evidence_json
                FROM analytics.signal_funnel_stage_v1
                WHERE signal_funnel_snapshot_id=%s
                ORDER BY stage_order
            """, (latest["signal_funnel_snapshot_id"],))
            stages = [dict(row) for row in cur.fetchall()]

        comparable = all(
            row.get("previous_stage_count") is None
            or int(row.get("stage_count") or 0) <= int(row.get("previous_stage_count") or 0)
            for row in stages
        )

        cur.execute("SELECT signal_funnel_reason_snapshot_id FROM analytics.signal_funnel_reason_snapshot_v1 ORDER BY created_at DESC LIMIT 1")
        reason_latest = cur.fetchone()
        reasons: list[dict[str, Any]] = []
        if reason_latest:
            cur.execute("""
                SELECT r.reason_group,sum(r.rows_total) AS rows_total,count(*) AS reason_values,
                       p.action_target
                FROM analytics.signal_funnel_reason_v1 r
                JOIN presentation.control_center_reason_policy_v1 filter
                  ON filter.reason_group=r.reason_group
                 AND filter.source_schema=r.source_schema
                 AND filter.source_table=r.source_table
                 AND filter.reason_column=r.reason_column
                 AND r.reason_value ~ filter.reason_value_pattern
                 AND filter.enabled
                JOIN presentation.control_center_recommendation_route_v1 p
                  ON p.reason_group=r.reason_group AND p.enabled
                WHERE r.signal_funnel_reason_snapshot_id=%s
                GROUP BY r.reason_group,p.action_target
                ORDER BY sum(rows_total) DESC
                LIMIT 8
            """, (reason_latest["signal_funnel_reason_snapshot_id"],))
            reasons = [dict(row) for row in cur.fetchall()]
        return stages, reasons, comparable

    @staticmethod
    def _shadow(cur) -> dict[str, Any]:
        cur.execute("SELECT to_regclass('analytics.forward_edge_shadow_trade_v1') AS table_name")
        if not cur.fetchone()["table_name"]:
            return {"total": 0, "pending": 0, "open": 0, "closed": 0, "net_pnl": 0, "unsafe": 0}
        cur.execute("SELECT cohort_id FROM analytics.forward_edge_incubator_v1 ORDER BY created_at DESC LIMIT 1")
        latest = cur.fetchone()
        if not latest:
            return {"total": 0, "pending": 0, "open": 0, "closed": 0, "net_pnl": 0, "unsafe": 0}
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
        """, (latest["cohort_id"],))
        result = dict(cur.fetchone() or {})
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
        """, (latest["cohort_id"],))
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
            """, (latest["cohort_id"],))
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
