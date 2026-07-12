from __future__ import annotations

import os
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
                funnel_stages, loss_reasons, funnel_comparable = self._signal_funnel(cur)

        return {
            "quality": quality,
            "relationships": relationships,
            "relationship_summary": summary,
            "forward": forward,
            "execution": execution,
            "funnel_stages": funnel_stages,
            "loss_reasons": loss_reasons,
            "funnel_comparable": funnel_comparable,
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
                SELECT reason_group,sum(rows_total) AS rows_total,count(*) AS reason_values
                FROM analytics.signal_funnel_reason_v1
                WHERE signal_funnel_reason_snapshot_id=%s
                GROUP BY reason_group
                ORDER BY sum(rows_total) DESC
                LIMIT 8
            """, (reason_latest["signal_funnel_reason_snapshot_id"],))
            reasons = [dict(row) for row in cur.fetchall()]
        return stages, reasons, comparable
