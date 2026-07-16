from __future__ import annotations

from typing import Any

import psycopg2
import psycopg2.extras


class OperatorDecisionV2Resolver:
    def resolve(self) -> tuple[dict[str, Any], ...]:
        with psycopg2.connect("postgresql:///finam_core") as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT decision_id,rank,transition_code,bottleneck_stage,loss_source_code,action_code,
                           source_identity,source_as_of,freshness_code,expected_profit_impact,
                           risk_impact_code,confidence,sample_size,sample_sufficiency_code,
                           policy_verdict,autonomy_mode,expires_at,rollback_plan_code,
                           baseline_value,measurement_due_at,measured_at,measurement_source_identity,
                           actual_result,feedback_status,quality_code,selection_status,updated_at
                    FROM analytics.operator_decision_workspace_v2
                    ORDER BY rank
                """)
                return tuple(dict(row) for row in cursor.fetchall())
